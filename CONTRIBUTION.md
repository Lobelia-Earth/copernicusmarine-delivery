# Contributing to Marine Producer Toolbox

## Release

Release are made by triggering the workflow from a `release/*` branch. The idea is to create this release branch if you do a new major or minor release. In the case where you are making a patch release, you can update the existing release branch (cherry-picking or merging changes).

To create a new release of the Marine Producer Toolbox, follow these steps:

0. Ensure the version in the `pyproject.toml` file is updated to the new release version.

1. (Locally) Checkout the `release/*` branch you want to create the release from.

    a. If the release branch does not exist, create it from the `main` branch.

    b. If the release branch exists and you want to do a patch release, make sure to update this branch with the fix you need.

2. (Locally) Push the release branch to the remote repository.

3. Trigger the release workflow from the `release/*` branch.

This will create both a new release in PyPI and a corresponding GitHub release with a tag.

The documentation should also trigger automatically to reflect the new release and update the new stable version of the documentation.
