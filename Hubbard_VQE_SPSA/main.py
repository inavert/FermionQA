"""
Main script for VQE optimization on Hubbard model.

Runs VQE calculation and outputs results, graphs, and report.
Usage: python main.py [--height H] [--width W] [--coulomb U] [--layer L] [--max-iter N]
"""

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
