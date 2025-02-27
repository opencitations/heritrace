# GitHub Actions CI/CD Setup

This repository uses GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

## Workflow Overview

The main workflow (`python-tests.yml`) runs on every push to any branch and on pull requests to the main branch. It:

1. Sets up Python (versions 3.10, 3.11, 3.12, and 3.13)
2. Installs Poetry using the dedicated GitHub Action
3. Installs project dependencies
4. Runs pytest with coverage reporting
5. Generates HTML coverage reports
6. Uploads coverage reports as artifacts for all branches and Python versions
7. Creates a coverage badge for each branch (using Python 3.10 test results)

## Coverage Badge Setup

The workflow uses the BYOB (Bring Your Own Badge) GitHub Action to generate coverage badges. To set this up:

1. Create a Personal Access Token (PAT) with access to the repository where badges will be stored
2. Add the token as a secret in your GitHub repository:
   - Go to your GitHub repository
   - Click on "Settings" > "Secrets and variables" > "Actions"
   - Click "New repository secret"
   - Name: `GIST_PAT`
   - Value: Your Personal Access Token
   - Click "Add secret"

The badge will be generated for each branch and will include the branch name in the badge label. The Python 3.10 test results are used for the badge generation.

## Local Testing

To run the same tests locally that GitHub Actions runs:

```bash
# Install dependencies including dev dependencies
poetry install --with dev

# Run tests with coverage
poetry run pytest --cov=heritrace
```

## Customizing the Workflow

You can customize the workflow by editing the `.github/workflows/python-tests.yml` file. Common customizations include:

- Changing the Python versions tested
- Modifying the branches that trigger the workflow
- Adjusting the coverage reporting settings
- Adding deployment steps after successful tests 