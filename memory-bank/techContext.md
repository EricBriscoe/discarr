# Technical Context: Discarr

## Technologies Used
- **Python**: 3.12+
- **Discord API Wrapper**: `discord.py`
- **HTTP Client**: `httpx`
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`
- **Linting**: `flake8`
- **Security Scanning**: `bandit`, `safety`
- **Containerization**: `Docker`, `docker-compose`

## Development Setup
1. **Clone Repository**: `git clone https://github.com/EricBriscoe/discarr.git`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Configure Environment**: Copy `.env.example` to `.env` and fill in API keys and URLs
4. **Run Bot**: `python src/main.py`
5. **Run Tests**: `python run_tests.py`

## Technical Constraints
- **Discord API Rate Limits**: All interactions must be mindful of Discord's rate limits
- **Async-only**: The entire codebase is asynchronous, requiring `async/await` for all I/O
- **Python 3.12+**: Requires a modern Python version
- **Network Latency**: Must handle potential delays when communicating with media servers
- **API Key Security**: API keys must be stored securely in `.env` and not committed to git

## Dependencies
- `discord.py`: For all Discord interactions
- `httpx`: For all external API calls
- `python-dotenv`: For loading environment variables
- `pytest`: For running the test suite
- `h2`: Optional, for HTTP/2 support in `httpx`

## Tool Usage Patterns
- **`pytest`**: Used for both unit and integration tests, with coverage reporting
- **`flake8`**: Enforces PEP 8 and other style conventions
- **`bandit`**: Scans for common security vulnerabilities in Python code
- **`safety`**: Checks for known vulnerabilities in dependencies
- **`docker-compose`**: Preferred method for production deployment

## API Usage
- **Radarr/Sonarr API v3**: The bot uses the v3 API for both services
- **Endpoints Used**:
  - `/api/v3/queue`: To get download queue information
  - `/api/v3/queue/{id}`: To remove items from the queue
  - `/api/v3/system/status`: To check service health
- **Authentication**: `X-Api-Key` header is used for all API requests
