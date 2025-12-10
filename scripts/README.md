# Docker Publish Script

This script builds and pushes the setlist-manager Docker image to your registry.

## Usage

### Basic usage (build and push with default settings)
```bash
python3 scripts/publish.py
```

### Specify a version
```bash
python3 scripts/publish.py 1.2.3
```

### Build locally without pushing
```bash
python3 scripts/publish.py --no-push
```

### Auto-increment version from docker-compose.yml
```bash
python3 scripts/publish.py --auto-version
```

### Custom registry
```bash
python3 scripts/publish.py --registry my-registry.com/setlist-manager
```

### Don't update docker-compose.yml
```bash
python3 scripts/publish.py --no-update-compose
```

## Options

- `version`: Image tag/version (default: 1.0.0)
- `--registry`: Image registry/name (default: registry.124bouchard.com/setlist-manager)
- `--no-push`: Build locally without pushing to registry
- `--no-update-compose`: Don't update docker-compose.yml after pushing
- `--auto-version`: Automatically increment version from docker-compose.yml

## Examples

Push a new version and update docker-compose.yml:
```bash
python3 scripts/publish.py --auto-version
```

Build locally for testing:
```bash
python3 scripts/publish.py 1.0.1 --no-push
```

Push to a different registry:
```bash
python3 scripts/publish.py 1.0.1 --registry my-registry.com/my-app
```

The script will:
1. Build the Docker image for linux/amd64 platform
2. Tag it with both the version and "latest"
3. Push to the registry (unless `--no-push` is used)
4. Update docker-compose.yml with the new version (unless `--no-update-compose` is used)