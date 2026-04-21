import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
import numpy as np
import cirq
import qsimcirq
from qiskit_algorithms.optimizers import SPSA

from models import Model
from circuits import prepare_variational_circuit
from observables import get_expectation_from_inner_product
from optimization import TerminationChecker
from storage import PickleStorage
from utils import setup_logger, obtain_initial_parameters, get_result_paths
from plotting import plot_energy_convergence, plot_parameter_evolution



class HubbardVQE:
    """Main VQE runner for Hubbard model."""

    def __init__(self, model: Model, layer: int, max_iter: int, backend_threads: int = 4):
        """
        Initialize VQE runner.

        Args:
            model: Hubbard model
            layer: Number of variational layers
            max_iter: Maximum iterations
            backend_threads: Number of CPU threads for backend
        """
        self.model = model
        self.layer = layer
        self.max_iter = max_iter
        self.backend_threads = backend_threads
        self.num_qubits = 2 * model.height * model.width

        # Initialize backend and qubits
        backend_options = qsimcirq.QSimOptions(
            max_fused_gate_size=2,
            cpu_threads=backend_threads
        )
        self.simulator = qsimcirq.QSimSimulator(backend_options)
        self.qubits = cirq.LineQubit.range(self.num_qubits)

        # Setup result paths
        self.result_paths = get_result_paths(model, layer)
        Path(self.result_paths['data']).parent.mkdir(parents=True, exist_ok=True)

        # Setup logging and storage
        self.logger = setup_logger(str(self.result_paths['log']))
        self.storage = PickleStorage(str(self.result_paths['data']))

        # Optimization tracking
        self.iteration_count = 0
        self.start_time = None
        self.end_time = None
        self.initial_energy = None
        self.final_energy = None

        self.logger.info(f"VQE Runner initialized for {model.height}x{model.width} Hubbard")
        self.logger.info(f"Parameters: U={model.coulomb}, N={model.particle}, Layers={layer}")

    def setup_parameters(self):
        """Initialize variational parameters."""
        self.param_dict = obtain_initial_parameters(
            self.model, self.layer, str(self.result_paths['data'])
        )
        self.param_resolver = cirq.ParamResolver(self.param_dict)
        self.logger.info(f"Variational parameters: {len(self.param_dict)}")

    def energy_function(self, parameters_array) -> float:
        """
        Calculate energy for given parameters.

        Args:
            parameters_array: Array of parameter values

        Returns:
            Energy value
        """
        for i, key in enumerate(self.param_resolver.param_dict.keys()):
            self.param_resolver.param_dict[key] = parameters_array[i]

        energy = get_expectation_from_inner_product(
            param_resolver=self.param_resolver,
            simulator=self.simulator,
            model=self.model,
            qubits=self.qubits,
            layer=self.layer,
            prepare_ansatz_function=prepare_variational_circuit
        )
        return energy

    def callback(self, nfev, parameters, value, stepsize, accepted):
        """Optimization callback for recording progress."""
        self.iteration_count += 1

        # Convert parameters to dictionary
        param_dict_current = {
            str(k): float(parameters[i])
            for i, k in enumerate(self.param_resolver.param_dict.keys())
        }

        # Record in storage
        self.storage.record(self.iteration_count, value, param_dict_current)

        # Log progress
        if self.iteration_count % 10 == 0:
            elapsed = time.time() - self.start_time
            self.logger.info(
                f"Iteration {self.iteration_count}: Energy={value:.6f}, "
                f"Elapsed={elapsed:.1f}s"
            )

    def run(self):
        """Execute VQE optimization."""
        print("=" * 70)
        print(f"HubbardVQE: {self.model.height}x{self.model.width} "
              f"(U={self.model.coulomb}, N={self.model.particle})")
        print("=" * 70)

        # Setup parameters
        self.setup_parameters()
        print(f"\n✓ Parameters initialized ({len(self.param_dict)} variables)")

        # Get initial energy
        self.start_time = time.time()
        initial_params = list(self.param_resolver.param_dict.values())
        self.initial_energy = self.energy_function(initial_params)

        # Record initial state
        param_dict_initial = {str(k): float(v) for k, v in self.param_dict.items()}
        self.storage.record(0, self.initial_energy, param_dict_initial)

        print(f"✓ Initial energy: {self.initial_energy:.6f}")
        self.logger.info(f"Initial energy: {self.initial_energy:.6f}")

        # Setup optimizer
        print(f"\n▶ Starting optimization ({self.max_iter} max iterations)...")
        termination_checker = TerminationChecker(window_size=50)
        optimizer = SPSA(
            maxiter=self.max_iter,
            termination_checker=termination_checker,
            callback=self.callback
        )

        # Run optimization
        result = optimizer.minimize(fun=self.energy_function, x0=initial_params)
        self.end_time = time.time()
        self.final_energy = result.fun

        # Save results
        self.storage.save()
        self.logger.info("Results saved to pickle file")

        # Print results
        elapsed_time = self.end_time - self.start_time
        improvement = self.initial_energy - self.final_energy

        print(f"\n✓ Optimization complete!")
        print(f"  Final energy: {self.final_energy:.6f}")
        print(f"  Improvement: {improvement:.6f}")
        print(f"  Iterations: {self.iteration_count}")
        print(f"  Time: {elapsed_time:.1f}s")
        print(f"  Results saved: {self.result_paths['data']}")

        self.logger.info(f"Final energy: {self.final_energy:.6f}")
        self.logger.info(f"Improvement: {improvement:.6f}")
        self.logger.info(f"Total time: {elapsed_time:.1f}s")

        return result

    def generate_report(self):
        """Generate and save report as text file."""
        data = self.storage.get_history()

        report_path = self.result_paths['data'].parent / f"{self.result_paths['data'].stem}_report.txt"

        report_lines = [
            "=" * 80,
            "HUBBARD MODEL VQE OPTIMIZATION REPORT",
            "=" * 80,
            "",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "MODEL PARAMETERS",
            "-" * 80,
            f"  Height:     {self.model.height}",
            f"  Width:      {self.model.width}",
            f"  Sites:      {self.model.sites}",
            f"  Coulomb U:  {self.model.coulomb}",
            f"  Particles:  {self.model.particle}",
            "",
            "QUANTUM CIRCUIT",
            "-" * 80,
            f"  Number of qubits:           {self.num_qubits}",
            f"  Ansatz layers:              {self.layer}",
            f"  Variational parameters:     {len(self.param_dict)}",
            "",
            "OPTIMIZATION RESULTS",
            "-" * 80,
            f"  Initial energy:             {self.initial_energy:.8f}",
            f"  Final energy:               {self.final_energy:.8f}",
            f"  Energy improvement:         {self.initial_energy - self.final_energy:.8f}",
            f"  Iterations completed:       {self.iteration_count}",
            f"  Execution time:             {self.end_time - self.start_time:.2f} seconds",
            "",
            "CONVERGENCE HISTORY",
            "-" * 80,
        ]

        # Add convergence details
        if data['energies']:
            report_lines.append(f"  Iteration 0:  {data['energies'][0]:.8f}")
            if len(data['energies']) > 1:
                mid_idx = len(data['energies']) // 2
                report_lines.append(f"  Iteration {mid_idx}: {data['energies'][mid_idx]:.8f}")
            if len(data['energies']) > 1:
                report_lines.append(f"  Iteration {len(data['energies'])-1}: {data['energies'][-1]:.8f}")

        report_lines.extend([
            "",
            "FILES GENERATED",
            "-" * 80,
            f"  Data (Pickle):  {self.result_paths['data'].name}",
            f"  Log file:       {self.result_paths['log'].name}",
            f"  Report:         {report_path.name}",
            f"  Energy plot:    {self.result_paths['plot'].name}",
            "",
            "=" * 80,
        ])

        report_text = "\n".join(report_lines)

        # Save report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"\n✓ Report saved: {report_path.name}")
        self.logger.info(f"Report saved: {report_path}")

        return report_text

    def plot_results(self):
        """Generate and save plots."""
        data = self.storage.get_history()

        print("\n▶ Generating plots...")

        # Energy convergence plot
        plot_energy_convergence(
            data,
            output_path=self.result_paths['plot'],
            title=f"Energy Convergence: {self.model.height}x{self.model.width} "
                  f"Hubbard (U={self.model.coulomb})"
        )
        print(f"✓ Energy plot: {self.result_paths['plot'].name}")

        # Parameter evolution plot (if there are parameters)
        if data['parameters'] and len(data['parameters'][0]) > 0:
            param_plot_path = self.result_paths['plot'].parent / \
                             f"{self.result_paths['plot'].stem}_parameters.png"
            plot_parameter_evolution(
                data,
                output_path=param_plot_path,
                title=f"Parameter Evolution: {self.model.height}x{self.model.width} Hubbard"
            )
            print(f"✓ Parameter plot: {param_plot_path.name}")

        self.logger.info("Plots generated successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VQE optimization for Hubbard model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python main.py                                    # Default: 1x4 model
        python main.py --height 1 --width 4 --coulomb 2  # Specify U=2
        python main.py --layer 2 --max-iter 200          # 2 layers, 200 iterations
                """
            )

    parser.add_argument('--height', type=int, default=1, help='Lattice height (default: 1)')
    parser.add_argument('--width', type=int, default=4, help='Lattice width (default: 4)')
    parser.add_argument('--coulomb', type=float, default=0, help='Coulomb interaction (default: 0)')
    parser.add_argument('--particle', type=int, default=None,
                        help='Number of particles (default: 2*width*height)')
    parser.add_argument('--layer', type=int, default=1, help='Ansatz layers (default: 1)')
    parser.add_argument('--max-iter', type=int, default=100, help='Max iterations (default: 100)')
    parser.add_argument('--threads', type=int, default=4, help='CPU threads (default: 4)')

    args = parser.parse_args()

    # Create model
    particle = args.particle if args.particle else 2 * args.height * args.width
    model = Model(
        height=args.height,
        width=args.width,
        coulomb=args.coulomb,
        particle=particle
    )

    # Run VQE
    vqe = HubbardVQE(
        model=model,
        layer=args.layer,
        max_iter=args.max_iter,
        backend_threads=args.threads
    )

    try:
        # Run optimization
        vqe.run()

        # Generate outputs
        report = vqe.generate_report()
        vqe.plot_results()

        # Print report summary
        print("\n" + report)

        print("\n✓ All outputs generated successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Optimization interrupted by user")
        vqe.logger.warning("Optimization interrupted by user")
        return 1

    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        vqe.logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
