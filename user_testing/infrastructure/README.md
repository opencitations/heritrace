# HERITRACE Testing Infrastructure

Docker infrastructure for isolated and autonomous HERITRACE user testing using [Virtuoso Utilities](https://github.com/opencitations/virtuoso_utilities).

## Architecture

**Complete isolation for each participant**:
- Dedicated HERITRACE container
- Separate Virtuoso databases (dataset + provenance) launched with Virtuoso Utilities
- Isolated Redis for cache/counters
- Unique ports for parallel access
- Test-specific configuration
- Automated data loading using Virtuoso bulk loader

## Prerequisites

- Docker and Docker Compose
- [Virtuoso Utilities](https://github.com/opencitations/virtuoso_utilities) installed globally with pipx:
  ```bash
  pipx install virtuoso-utilities
  ```

## Quick Setup

### 1. Host Preparation

```bash
# Ensure you have Docker and Docker Compose
docker --version
docker compose --version

# Verify Virtuoso Utilities is installed
virtuoso-launch --help

# Clone and navigate to infrastructure directory
cd user_testing/infrastructure
```

### 2. User Environment Creation

The setup script now requires the participant's ORCID iD.
The setup script automatically creates environments in "Demo Mode".

```bash
# Example for a technician 
./setup-user-environment.sh user001 technician

# Example for an end user
./setup-user-environment.sh user101 enduser
```

### 3. Environment Management

```bash
# Start (automatically launches Virtuoso with Virtuoso Utilities and loads test data)
./manage-environments.sh start user001

# Status of all environments
./manage-environments.sh status

# Stop specific
./manage-environments.sh stop user001

# Complete reset (delete all modifications)
./manage-environments.sh reset user001
```

## Testing Workflow

### For Technicians
1. **Setup**: Environment with reduced SHACL/display rules
2. **Tasks**: Add `dcterms:abstract`, `prism:keyword`, display rules
3. **Verification**: Export modified configurations

### For End Users  
1. **Setup**: Complete environment with test data loaded from test_data.nq.gz
2. **Tasks**: Creation, modification, merge, restore entities
3. **Verification**: Export metadata modifications

## Authentication

Authentication is handled via **an automatic, privacy-preserving demo mode**.
- The system **does not** use real ORCID accounts for testing.
- When an environment is started, the participant is automatically logged in with a synthetic, session-specific user identity (e.g., "Demo User (user001)").
- This synthetic user is assigned a valid, unique ORCID iD that is generated deterministically for their session.
- This approach ensures participant privacy and data reproducibility, as no personal information is collected, while still allowing for provenance tracking.
- All references to ORCID in the user interface are part of the simulation.

## Directory Structure

```
infrastructure/
├── setup-user-environment.sh         # Environment creation
├── manage-environments.sh            # Environment management
├── users/                           # Directory for each user
│   ├── user001/
│   │   ├── .env                    # Specific variables
│   │   ├── docker-compose.yml      # HERITRACE + Redis only
│   │   ├── config.py               # HERITRACE configuration
│   │   ├── resources/              # SHACL & display rules
│   │   ├── data/                   # test_data.nq.gz for bulk loading
│   │   ├── dataset-data/           # Virtuoso dataset container data
│   │   ├── prov-data/              # Virtuoso provenance container data
│   │   └── ACCESS_INFO.txt        # User access info
│   └── user002/...
└── exports/                        # Final exports for analysis
    ├── user001-20240101-120000/
    └── user002-20240101-130000/
```

## Port Configuration

**Automatic scheme**: User `userXXX` → ports `5100 + XXX*10`

Example:
- `user001`: HERITRACE `https://127.0.0.1:5110`, Redis 5111, Dataset 5112, Prov 5113  
- `user002`: HERITRACE `https://127.0.0.1:5120`, Redis 5121, Dataset 5122, Prov 5123

Additional ports for Virtuoso ISQL access: Dataset+100, Prov+100

## Useful Commands

### Batch Creation

```bash
# Create 2 technician environments
./setup-user-environment.sh user001 technician
./setup-user-environment.sh user002 technician

# Create 2 end user environments
./setup-user-environment.sh user101 enduser
./setup-user-environment.sh user102 enduser
```

### Monitoring

```bash
# List all environments
./manage-environments.sh list

# Detailed status
./manage-environments.sh status

# Verify Docker resources
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Export Results

```bash
# Export single user
./manage-environments.sh export user001

# Batch export of all active users
for user in $(docker ps --format "{{.Names}}" | grep heritrace- | sed 's/heritrace-//'); do
    ./manage-environments.sh export $user
done
```

## Troubleshooting

### Container won't start
```bash
# Check free ports
netstat -tlnp | grep :5110

# Check Virtuoso Utilities logs
docker logs virtuoso-dataset-user001

# Detailed HERITRACE logs
cd users/user001 && docker compose logs
```

### Database not initialized
```bash
# Complete environment reset
./manage-environments.sh reset user001
./manage-environments.sh start user001
```

### Resource cleanup
```bash
# Complete environment removal
./manage-environments.sh cleanup

# Remove user directory
rm -rf users/user001
```

## Analysis Integration

### Exported Data

Each export contains:
- `final_dataset.ttl`: Final dataset with user modifications
- `provenance.ttl`: Modification log (automatic tracking)
- `shacl.ttl`: Final SHACL schema (if modified by technicians)
- `display_rules.yaml`: Final display rules (if modified)
- `export_summary.txt`: Session metadata

### Comparative Analysis

```bash
# Compare dataset modifications (decompress first)
gunzip -c test_materials/test_data.nq.gz > test_materials/test_data.nq
# Then compare with exported final_dataset.ttl

# Verify technician task success
shacl validate --schema exports/user001-*/shacl.ttl --data test_materials/test_data.nq
```

## Scalability

**Resources per user**:
- RAM: ~3.5GB (HERITRACE + 2 Virtuoso instances + Redis)
- Storage: ~500MB (database + cache)
- Ports: 4 consecutive ports + 2 additional ISQL ports

**Typical limits**:
- 8GB RAM host: ~2 simultaneous users
- 16GB RAM host: ~4-5 simultaneous users
- 32GB RAM host: ~8-10 simultaneous users

**Optimizations**:
- Staggered startup to reduce load peaks
- Automatic cleanup of inactive environments
- Export compression to reduce storage 