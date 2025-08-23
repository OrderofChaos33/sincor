# SINCOR

**Synthetic Intelligent Noncustodial Consensus Operations Registry**

A Decentralized Autonomous Enterprise powered by agent-based compliance, scheduling, and content systems.

## Features

- **Agent Framework**: Multi-agent system with specialized roles
- **Lead Capture**: Web-based lead generation for detailing business
- **Content Pipeline**: Automated storyboard and video generation
- **Compliance Layer**: KYC/AML/SEC monitoring agents

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SINCOR/_local_overrides/sincor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp config/environment.sample.env config/.env
# Edit config/.env with your actual values
```

4. Run the application:
```bash
python sincor_app.py
```

The application will start on `http://127.0.0.1:5000`

## Configuration

### Environment Variables

Copy `config/environment.sample.env` to `config/.env` and configure:

- **Email Settings**: SMTP configuration for lead notifications
- **Application**: PORT setting for the web server
- **API Keys**: Various service integrations

### Agent Configuration

Agent roles are defined in `config/agent_roles.yaml`:
- `gazette`: KYC, AML, SEC compliance agents
- `paydae`: Logging and reward trigger agents

## Usage

### Web Interface

- `/` - Home page with navigation
- `/lead` - Lead capture form
- `/logs` - View application logs
- `/outputs` - Access generated files
- `/health` - Health check endpoint

### Agent Framework

```python
from agents.oversight.oversight_agent import OversightAgent

agent = OversightAgent(name="MyAgent", log_path="logs/my_agent.log")
agent.heartbeat()
diagnostics = agent.run_diagnostics()
```

## Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

## Project Structure

```
SINCOR/
├── agents/              # Agent implementations
│   ├── gazette/         # Compliance agents (KYC, AML, SEC)
│   ├── marketing/       # Content generation agents
│   ├── oversight/       # System monitoring agents
│   ├── paydae/          # Payment and reward agents
│   └── taskpool/        # Task management agents
├── config/              # Configuration files
├── docs/                # Documentation
├── logs/                # Application logs
├── outputs/             # Generated content
├── public/              # Public assets
├── scripts/             # Utility scripts
├── tests/               # Test suite
└── sincor_app.py        # Main web application
```

## Security

⚠️ **Important Security Notes:**

- Never commit `.env` files containing real credentials
- Use strong, unique passwords for email accounts
- Enable 2FA and use app passwords for Gmail/Outlook
- Review logs regularly for suspicious activity

## Development

### Adding New Agents

1. Create agent class in appropriate `agents/` subdirectory
2. Implement standard agent interface (heartbeat, diagnostics)
3. Add configuration to `config/agent_roles.yaml`
4. Write tests in `tests/test_<agent_name>.py`

### Running in Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
export FLASK_ENV=development
python sincor_app.py
```

## Deployment

### Production Checklist

- [ ] Configure proper SMTP settings
- [ ] Set strong environment variables
- [ ] Enable HTTPS with proper certificates
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Create backup procedures

### Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "sincor_app.py"]
```

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [documentation](docs/)
2. Review [logs](logs/) for error messages
3. Run diagnostics: `GET /health`
4. Check agent status with oversight tools