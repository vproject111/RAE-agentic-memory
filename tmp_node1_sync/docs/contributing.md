# Contributing to RAE Agentic Memory

First off, thank you for considering contributing to RAE! We welcome contributions of all kinds, from bug fixes and new features to documentation improvements.

To ensure a smooth and collaborative process, we've outlined a few guidelines below.

## Code of Conduct

We have a [Code of Conduct](./CODE_OF_CONDUCT.md) that all contributors are expected to follow. Please make sure you have read and understood it.

## Setting Up Your Development Environment

A great developer experience is important to us. We've streamlined the setup process as much as possible.

1.  **Fork & Clone**: Fork the repository on GitHub and clone it to your local machine.
    ```bash
    git clone https://github.com/YOUR-USERNAME/RAE-agentic-memory.git
    cd RAE-agentic-memory
    ```

2.  **Install Dependencies**: We use a `Makefile` to manage dependencies for all parts of the project.
    ```bash
    make install
    ```
    This command will create a virtual environment (`.venv`) and install all necessary Python packages.

3.  **Install Pre-Commit Hooks**: We use `pre-commit` to automatically lint and format code before it's committed. This helps maintain a consistent codebase.
    ```bash
    # Activate the virtual environment first
    source .venv/bin/activate
    
    # Install the hooks
    pre-commit install
    ```
    Now, `ruff` will automatically check and format your files every time you run `git commit`.

4.  **Start Infrastructure**: The core services run in Docker.
    ```bash
    make up
    ```

## Contribution Workflow

1.  **Create a Branch**: Create a new, descriptive branch for your feature or bugfix.
    ```bash
    git checkout -b feat/my-new-feature  # For features
    git checkout -b fix/a-specific-bug    # For bug fixes
    ```

2.  **Make Changes**: Write your code! As you work, make sure to:
    *   **Follow Style Guides**: The `pre-commit` hooks will handle most of this for you.
    *   **Add Tests**: Any new feature or bug fix should be accompanied by tests. Use `pytest` to run them:
        ```bash
        make test
        ```
    *   **Update Documentation**: If you're adding a new feature or changing behavior, update the relevant documentation in the `docs/` directory.

3.  **Commit Your Changes**: We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. This helps us automate changelogs and versioning.
    *   `feat:`: A new feature.
    *   `fix:`: A bug fix.
    *   `docs:`: Documentation only changes.
    *   `style:`: Changes that do not affect the meaning of the code (white-space, formatting, etc).
    *   `refactor:`: A code change that neither fixes a bug nor adds a feature.
    *   `test:`: Adding missing tests or correcting existing tests.
    *   `chore:`: Changes to the build process or auxiliary tools.

    Example:
    ```bash
    git commit -m "feat(api): add new endpoint for memory summarization"
    ```

4.  **Push and Create a Pull Request**: Push your branch to your fork and open a Pull Request against the `main` branch of the upstream repository. Provide a clear description of your changes and link to any relevant issues.

## Reporting Bugs and Suggesting Features

If you're not ready to contribute code, you can still help!

*   **Report Bugs**: If you find a bug, please [open an issue](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues) and provide as much detail as possible.
*   **Suggest Enhancements**: Have an idea for a new feature? We'd love to hear it. Open an issue to start the discussion.

Thank you for helping make RAE better!