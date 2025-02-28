# Release Process

This project uses [semantic-release](https://github.com/semantic-release/semantic-release) to automate the release process. The release workflow is triggered when a commit is pushed to the `main` branch with the keyword `[release]` in the commit message.

## How to create a new release

1. Make sure your changes are committed and pushed to the `main` branch
2. Include the keyword `[release]` in your commit message, for example:
   ```
   git commit -m "feat: add new feature [release]"
   ```
   or
   ```
   git commit -m "[release] feat: add new feature"
   ```

3. Push your changes to the `main` branch:
   ```
   git push origin main
   ```

4. The release workflow will automatically:
   - Determine the next version number based on commit messages
   - Update the version in pyproject.toml
   - Create a CHANGELOG.md file or update it
   - Create a GitHub release with release notes

## Release Types

Semantic versioning (SemVer) uses a three-part version number: `MAJOR.MINOR.PATCH`. The release type is determined by the commit messages:

- **Patch Release (0.0.x)**: Contains bug fixes only. Created when commits with `fix:` prefix are included.
- **Minor Release (0.x.0)**: Contains new features that don't break existing functionality. Created when commits with `feat:` prefix are included.
- **Major Release (x.0.0)**: Contains breaking changes. Created when commits include `BREAKING CHANGE:` in the commit body or footer, or when the commit type has an exclamation mark (e.g., `feat!:`).

### Creating a Major Release

To create a major release, you need to indicate a breaking change in your commit message. There are two ways to do this:

1. **Using the exclamation mark**:
   ```
   git commit -m "feat!: completely redesign API [release]"
   ```

2. **Using the BREAKING CHANGE footer**:
   ```
   git commit -m "feat: update user authentication
   
   BREAKING CHANGE: The authentication process now requires a different token format [release]"
   ```

Either of these commit formats will trigger a major version bump when the release workflow runs.

## Commit Message Format

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification. Your commit messages should be structured as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The `type` field must be one of the following:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to our CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

### Examples

```
feat: add new feature X
```

```
fix: resolve issue with function Y
```

```
docs: update README with new instructions
```

```
feat(api): add new endpoint for user authentication
```