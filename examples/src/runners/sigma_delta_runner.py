"""First-order sigma-delta modulator: run transient, compute PSD and metrics."""

from pathlib import Path
import numpy as np

from pade.statement import Statement, Analysis, Save, Options
from pade.backends.ngspice.simulator import NgspiceSimulator
from pade.backends.ngspice.results_reader import read_raw
from pdk.sky130.config import config
from src.testbenches.sigma_delta import SigmaDeltaTranTB


class SigmaDeltaRunner:
    """Runner for first-order sigma-delta transient and FFT evaluation.

    Args:
        dut_class: Cell class for the modulator DUT (default: SigmaDelta1).
        vdd: Supply voltage.
        fin: Input sine frequency (Hz).
        ampl: Input sine amplitude (peak, around vdd/2).
        fs: Sampling clock frequency (Hz).
        osr: Oversampling ratio.  Signal bandwidth = fs / (2 * osr).
        cs, cf, caz: Capacitor values (F).
        gm, r: OTA transconductance and output resistance.
    """

    def __init__(self, dut_class=None, vdd: float = 1.8, fin: float = 1e3,
                 ampl: float = 0.1, fs: float = 128e3, osr: int = 64,
                 cs: float = 0.25e-12, cf: float = 1e-12,
                 caz: float = 1e-12, gm: float = 1e-3, r: float = 1e6):
        self.dut_class = dut_class
        self.vdd = vdd
        self.fin = fin
        self.ampl = ampl
        self.fs = fs
        self.osr = osr
        self.cs = cs
        self.cf = cf
        self.caz = caz
        self.gm = gm
        self.r = r
        self.simulator = NgspiceSimulator(output_dir=config.sim_data_dir / 'sigma_delta')

    @property
    def bw(self) -> float:
        """Signal bandwidth (Hz)."""
        return self.fs / (2 * self.osr)

    def _build_tb(self) -> SigmaDeltaTranTB:
        kwargs = dict(
            vdd=self.vdd, fin=self.fin, ampl=self.ampl, fs=self.fs,
            cs=self.cs, cf=self.cf, caz=self.caz, gm=self.gm, r=self.r,
        )
        if self.dut_class is not None:
            kwargs['dut_class'] = self.dut_class
        return SigmaDeltaTranTB(**kwargs)

    def _build_statements(self, n_periods: int) -> list:
        duration = n_periods / self.fs
        step = 1 / (self.fs * 20)
        vcm = self.vdd / 2
        return [
            Options(method='gear', reltol=0.01, trtol=7),
            Statement(f'.lib "{config.sky130_lib}" tt'),
            Statement('.options interp'),
            Statement(f'.ic v(vint)={vcm} v(out)={self.vdd} v(outb)=0'),
            Analysis('tran', stop=duration, step=step, uic=True),
            Save(['vin', 'out', 'vint', 'phi1', 'phi2']),
        ]

    def run(self, n_periods: int = 8192) -> Path:
        tb = self._build_tb()
        statements = self._build_statements(n_periods)
        return self.simulator.simulate(tb, statements, 'run', show_output=False)

    def evaluate(self, raw_file: Path) -> dict:
        data = read_raw(raw_file)
        return {
            'time': data['time'],
            'vin': data['v(vin)'],
            'out': data['v(out)'],
            'vint': data['v(vint)'],
            'phi1': data['v(phi1)'],
            'phi2': data['v(phi2)'],
        }

    def run_and_evaluate(self, n_periods: int = 8192) -> dict:
        raw_file = self.run(n_periods)
        result = self.evaluate(raw_file)
        result['raw_file'] = raw_file
        return result

    def psd_and_metrics(self, result: dict, n_skip: int = 5) -> tuple[np.ndarray, np.ndarray, dict]:
        """Resample output at fs, compute PSD and in-band metrics.

        Args:
            result: Dict from evaluate().

        Returns:
            (freqs, psd_dB, metrics) where metrics contains SNR, SNDR, ENOB,
            HD2, HD3 and FFT metadata.
        """
        time, out = result['time'], result['out']
        fs, fin, bw = self.fs, self.fin, self.bw

        # Resample at exactly fs (one sample per clock cycle)
        t_start = (n_skip + 0.25) / fs
        t_end = time[-1]
        n_total = int((t_end - t_start) * fs)
        # Round down to power of 2 for clean FFT
        n_fft = 2 ** int(np.floor(np.log2(n_total)))
        t_uniform = t_start + np.arange(n_fft) / fs
        out_resampled = np.interp(t_uniform, time, out)

        # Remove DC, apply Hann window
        out_resampled -= np.mean(out_resampled)
        window = np.hanning(n_fft)
        out_w = out_resampled * window

        # FFT, single-sided power spectrum
        X = np.fft.rfft(out_w)
        freqs = np.fft.rfftfreq(n_fft, 1 / fs)
        # Normalized PSD (power per bin, corrected for window)
        psd = (np.abs(X) ** 2) / (np.sum(window ** 2))
        psd_dB = 10 * np.log10(psd + 1e-30)

        # In-band metrics
        df = fs / n_fft
        k_sig = int(round(fin / df))
        k_h2 = 2 * k_sig
        k_h3 = 3 * k_sig
        k_band = int(round(bw / df))

        # Signal power (bin around fin)
        sig_bins = range(max(k_sig - 1, 0), min(k_sig + 2, len(psd)))
        signal_power = np.sum(psd[list(sig_bins)])

        # In-band noise (exclude signal and harmonics)
        noise_mask = np.zeros(len(psd), dtype=bool)
        noise_mask[1:k_band] = True
        for k in [k_sig, k_h2, k_h3]:
            for offset in range(-1, 2):
                idx = k + offset
                if 0 <= idx < len(noise_mask):
                    noise_mask[idx] = False
        noise_power = np.sum(psd[noise_mask])

        # Harmonic distortion
        h2_power = np.sum(psd[max(k_h2-1,0):min(k_h2+2,len(psd))]) if k_h2 < k_band else 0
        h3_power = np.sum(psd[max(k_h3-1,0):min(k_h3+2,len(psd))]) if k_h3 < k_band else 0

        snr = 10 * np.log10(signal_power / (noise_power + 1e-30))
        sndr = 10 * np.log10(signal_power / (noise_power + h2_power + h3_power + 1e-30))
        enob = (sndr - 1.76) / 6.02

        metrics = {
            'SNR_dB': snr, 'SNDR_dB': sndr, 'ENOB': enob,
            'HD2_dBc': 10 * np.log10((h2_power + 1e-30) / (signal_power + 1e-30)),
            'HD3_dBc': 10 * np.log10((h3_power + 1e-30) / (signal_power + 1e-30)),
            'n_fft': n_fft,
        }
        return freqs, psd_dB, metrics
