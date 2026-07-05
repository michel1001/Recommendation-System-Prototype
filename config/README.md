# Configuration

## Purpose
This directory contains configuration files for the ML sector monitoring prototype.

## Files
- **config.py**: Main configuration file
- **logging_config.py**: Logging configuration
- **model_params.py**: Model hyperparameters and thresholds
- **.env.example**: Template for environment variables

## Usage
1. Copy `.env.example` to `.env` and fill in sensitive values
2. Load config in your application: `from config.config import Config`
3. Never commit actual `.env` files with secrets
