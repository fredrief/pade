from pade.evaluation import Signal
import shlib
from skillbridge import Workspace
from inform import warn, log

class SkillSignal:
    def __init__(self, name, analysis, data_access, spectre_name=None) -> None:
        self.name = name
        self.analysis = analysis
        self.data_access = data_access
        self.spectre_name = spectre_name if not spectre_name is None else name


    def print_skill_def(self):
        """
        Prints the definition
        """
        return f'{self.name} = {self.data_access}("{self.spectre_name}" ?result "{self.analysis}-{self.analysis}")'

class SkillExpr:
    """
    An expression understood by skill
    """
    def __init__(self, name, skill_expr: str, *signals: SkillSignal, append=False, **kwargs) -> None:
        """
        Expression should be on the form:
            "log10(difference(VOP VON))**2"
        """
        self.name = name
        self.skill_expr = skill_expr
        self.signals = signals
        self.append = append
        self.kwargs = kwargs

    def print_skill_def(self):
        """
        Prints the definition
        """
        s = ''
        if not self.append:
            s += 'wid = awvCreatePlotWindow()\n'
        else:
            s += 'wid = awvGetCurrentWindow()\n'
        s += f'{self.name} = "{self.skill_expr}"\n'
        s += f'awvPlotExpression(wid {self.name} nil ?expr list("{self.name}")'
        for key, value in self.kwargs.items():
            s += f' ?{key} list("{value}")'
        s += ')\n'
        return s

class SkillVIVAPlot:
    """
    Plot in VIVA using skill
    """
    def __init__(self, expressions=[]) -> None:
        """
        Expression should be on the form:
            "log10(difference(VOP VON))**2"
        """
        self.signals = {}
        self.expressions = []
        self.script_filename = 'plot.il'
        for expr in expressions:
            self.add_expr(expr)

    def add_expr(self, expr: SkillExpr) -> None:
        """
        Add SkillExpr
        """
        # Add signal to signal list
        for sig in expr.signals:
            if not sig.name in self.signals:
                self.signals[sig.name] = sig

        self.expressions.append(expr)

    def plot(self, skill_dir, res_dir,):
        """
        Open plot in Viva
        """
        # Try to open connection to server
        try:
            ws = Workspace.open()
        except Exception as e:
            warn(f'SkillPlot could not establish connection to server: {e}')
            return
        # Set path
        self.skill_dir = skill_dir
        self.res_dir = res_dir

        # info(f'Running skill plot script: {shlib.to_path(self.skill_dir, self.script_filename)}')
        # Write skill script
        self.print_skill()
        # Launch script
        ws['load'](str(shlib.to_path(self.skill_dir, self.script_filename)))


    def print_skill(self):
        s = ''
        s += f'res_dir = "{self.res_dir}"\n'
        s += f'openResults(res_dir)\n'
        for name, sig in self.signals.items():
            s += f'{sig.print_skill_def()}\n'

        for expr in self.expressions:
            s += expr.print_skill_def()

        with open(shlib.to_path(self.skill_dir, self.script_filename), 'w') as f:
            f.write(s)






