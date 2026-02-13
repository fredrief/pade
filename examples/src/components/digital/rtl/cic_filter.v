/*
 * CIC (Cascaded Integrator-Comb) Decimation Filter
 *
 * Fixed-order CIC decimation filter for sigma-delta bitstream processing.
 * N integrator stages at full clock rate, followed by a decimation counter,
 * then N comb (differentiator) stages at the decimated rate.
 *
 * No multipliers — only additions, subtractions, and registers.
 *
 * Parameters:
 *   ORDER             - Number of CIC stages (default 3)
 *   DECIMATION_RATIO  - Decimation factor R (default 64)
 *   INPUT_WIDTH       - Bit width of input (1 for sigma-delta bitstream)
 *   OUTPUT_WIDTH      - Bit width of output
 *
 */

module cic_filter #(
    parameter ORDER            = 3,
    parameter DECIMATION_RATIO = 64,
    parameter INPUT_WIDTH      = 1,
    parameter OUTPUT_WIDTH     = 16
) (
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire signed [INPUT_WIDTH-1:0] din,
    output reg  signed [OUTPUT_WIDTH-1:0] dout,
    output reg                        valid
);

    // Internal width: enough bits to avoid overflow (Hogenauer)
    // ACC_WIDTH = INPUT_WIDTH + ORDER * ceil(log2(R))
    localparam ACC_BITS = $clog2(DECIMATION_RATIO);
    localparam ACC_WIDTH = INPUT_WIDTH + ORDER * ACC_BITS;

    // Counter for decimation
    localparam CNT_WIDTH = $clog2(DECIMATION_RATIO);
    reg [CNT_WIDTH-1:0] count;
    wire decimate_tick = (count == DECIMATION_RATIO - 1);

    // Integrator registers
    reg signed [ACC_WIDTH-1:0] integ [0:ORDER-1];

    // Comb delay registers and outputs
    reg signed [ACC_WIDTH-1:0] comb_delay [0:ORDER-1];
    reg signed [ACC_WIDTH-1:0] comb_out   [0:ORDER-1];

    integer i;

    // ---------------------------------------------------------------------------
    // Integrator section (runs at full clock rate)
    // ---------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < ORDER; i = i + 1)
                integ[i] <= 0;
        end else begin
            // First integrator: accumulate input
            integ[0] <= integ[0] + {{(ACC_WIDTH - INPUT_WIDTH){din[INPUT_WIDTH-1]}}, din};
            // Subsequent integrators: accumulate previous integrator output
            for (i = 1; i < ORDER; i = i + 1)
                integ[i] <= integ[i] + integ[i-1];
        end
    end

    // ---------------------------------------------------------------------------
    // Decimation counter
    // ---------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 0;
        else if (decimate_tick)
            count <= 0;
        else
            count <= count + 1;
    end

    // ---------------------------------------------------------------------------
    // Comb section (updates at decimated rate)
    // ---------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < ORDER; i = i + 1) begin
                comb_delay[i] <= 0;
                comb_out[i]   <= 0;
            end
            dout  <= 0;
            valid <= 1'b0;
        end else if (decimate_tick) begin
            // First comb: difference of last integrator output
            comb_out[0]   <= integ[ORDER-1] - comb_delay[0];
            comb_delay[0] <= integ[ORDER-1];
            // Subsequent combs
            for (i = 1; i < ORDER; i = i + 1) begin
                comb_out[i]   <= comb_out[i-1] - comb_delay[i];
                comb_delay[i] <= comb_out[i-1];
            end
            // Truncate to output width (take MSBs)
            dout  <= comb_out[ORDER-1][ACC_WIDTH-1 -: OUTPUT_WIDTH];
            valid <= 1'b1;
        end else begin
            valid <= 1'b0;
        end
    end

endmodule
