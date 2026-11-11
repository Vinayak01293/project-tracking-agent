# Project Tracking Agent

A Python-based multi-agent application that routes project-tracking
questions to specialist agents for GitHub and Linear.

-   **GitHub Agent:** repositories, issues, pull requests, and starred
    repositories.
-   **Linear Agent:** assigned issues, projects, and teams.
-   **Orchestration Agent:** identifies the platform and operation,
    resolves the intended application user, asks for clarification when
    needed, and rejects out-of-scope questions.

The application uses FastAPI for its backend and serves a lightweight
browser-based chat interface from the same project. GitHub and Linear
credentials are encrypted before they are persisted.

------------------------------------------------------------------------

## Quick Start

Follow these steps to run the application locally from a fresh clone.

### 1. Clone the repository

``` bash
git clone https://github.com/Vinayak01293/project-tracking-agent.git
cd Project-Tracking-Agent
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the example:

**Windows PowerShell**

``` powershell
Copy-Item .env.example .env
```

**macOS / Linux**

``` bash
cp .env.example .env
```

Update `.env` with: - Your OpenRouter API key. - A valid Fernet
encryption key. - Your LangSmith API key if tracing is enabled.

Generate a Fernet key with:

``` bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use the generated value for `FERNET_KEY`. Keep this key unchanged after
registering integrations; otherwise, previously encrypted credentials
may not be decryptable.

### 5. Start the application

Run from the repository root:

``` bash
uvicorn main:app --reload
```

### 6. Open the application

  Service             URL
  ------------------- ------------------------------
  Chat application    http://localhost:8000
  API documentation   http://localhost:8000/docs
  Health check        http://localhost:8000/health

### 7. Register users and integrations

1.  Open the chat application.
2.  Select **Add User**.
3.  Enter the user's name and email.
4.  Add at least one integration: GitHub Personal Access Token and/or
    Linear API key.
5.  Submit and repeat for the other application user.

The application validates integration credentials with the provider
before saving the user. Credentials are encrypted before persistence.

### 8. Run a few verification queries

``` text
List Jyothir's repositories
Show Jyothir's open GitHub issues
Show Vinayak's starred repositories
Show Jyothir's open Linear issues
List Vinayak's Linear projects
```

Test clarification by asking:

``` text
Show me open pull requests
```

The application should ask which registered user's pull requests are
required. Reply with the user's name and verify that the original
request continues.

Test out-of-scope handling with an unrelated question. The expected
response is:

``` text
I cannot answer this question
```

------------------------------------------------------------------------

## Prerequisites

-   Python 3.11 or later.
-   Git.
-   OpenRouter API key and access to the configured model.
-   GitHub Personal Access Token(s) for the GitHub accounts to be
    connected.
-   Linear API key(s) for the Linear accounts to be connected.
-   LangSmith API key if LangSmith tracing is enabled.

Provider tokens must have the permissions and account access required to
read the data being queried.

> If two application users are registered with the same GitHub or Linear
> credential, both will access the same external provider identity. Use
> separate credentials to test distinct external accounts.

------------------------------------------------------------------------

## Project Structure

The backend and frontend are kept together in one project directory. The
frontend assets are served by FastAPI from the `static` directory.

``` text
Project-Tracking-Agent/
├── agents/
│   ├── github_agent/
│   ├── linear_agent/
│   └── orchestration_agent/
├── core/
│   ├── api/
│   ├── llm/
│   ├── models/
│   ├── platform/
│   ├── repository/
│   └── security/
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

------------------------------------------------------------------------

## Environment Configuration

Create `.env` in the repository root. Use `.env.example` as the
template.

  ----------------------------------------------------------------------------------
  Variable                                            Required Purpose
  ------------------------------- ---------------------------- ---------------------
  `FERNET_KEY`                                             Yes Fernet key used to
                                                               encrypt and decrypt
                                                               stored integration
                                                               credentials.

  `OPENROUTER_MODEL`                                       Yes Model identifier used
                                                               by the LLM
                                                               configuration.

  `OPENROUTER_API_KEY`                                     Yes Authenticates
                                                               requests to
                                                               OpenRouter.

  `LANGSMITH_TRACING`                                 Optional Enables or disables
                                                               LangSmith tracing.

  `LANGSMITH_ENDPOINT`                                Optional LangSmith API
                                                               endpoint.

  `LANGSMITH_API_KEY`                 Optional when tracing is Authenticates
                                                      disabled LangSmith tracing.

  `LANGSMITH_AGENT_ID`                                Optional LangSmith
                                                               project/agent
                                                               identifier configured
                                                               for this application.

  `LANGSMITH_AGENT_ENVIRONMENT`                       Optional Environment label
                                                               attached to tracing.
  ----------------------------------------------------------------------------------

Keep `.env` local. Do not commit API keys, Fernet keys, or other
secrets. Commit `.env.example` with placeholders only.

------------------------------------------------------------------------

## Architecture and Request Flow

``` text
Browser UI
   |
   v
FastAPI
   |
   v
Orchestration Agent
   |-- Identify platform (GitHub / Linear)
   |-- Identify operation and filters
   |-- Resolve target application user
   |-- Ask for clarification if identity is ambiguous
   |-- Reject unsupported questions
   |
   +-----------------------+
   |                       |
   v                       v
GitHub Agent           Linear Agent
   |                       |
   v                       v
GitHub REST API         Linear GraphQL API
   |                       |
   +-----------+-----------+
               |
               v
         Response to UI
```

The orchestration layer selects the specialist agent and target
application user. Credential lookup and decryption are performed by
application code; the model does not get to select arbitrary credentials
based on user input.

### Supported operations

  -----------------------------------------------------------------------
  Platform                            Operation
  ----------------------------------- -----------------------------------
  GitHub                              List repositories

  GitHub                              List issues

  GitHub                              List pull requests authored by the
                                      authenticated GitHub account

  GitHub                              List starred repositories

  Linear                              List issues assigned to the
                                      authenticated Linear account

  Linear                              List projects accessible to the
                                      authenticated Linear account

  Linear                              List teams accessible to the
                                      authenticated Linear account
  -----------------------------------------------------------------------

The current operations are read-only.

------------------------------------------------------------------------

## Testing

Run commands from the repository root with the virtual environment
activated.

### Specialist agent tests

The repository includes test scripts under `tests/`. For example:

``` bash
python tests/linear_agent_tests.py
python tests/github_agent_test-script.py
```

These scripts help test provider connectivity and specialist-agent
behavior independently of the orchestration flow.

### Manual end-to-end checks

Verify all of the following:

1.  GitHub requests route to the GitHub Agent.
2.  Linear requests route to the Linear Agent.
3.  Requests naming a user use that user's provider integration.
4.  Requests with an ambiguous target user ask for clarification.
5.  The original request is preserved after clarification.
6.  Out-of-scope questions return exactly
    `I cannot answer this question`.
7.  Results from two different external accounts are isolated when
    distinct credentials are configured.

------------------------------------------------------------------------

## Troubleshooting

  ------------------------------------------------------------------------
  Problem                             What to check
  ----------------------------------- ------------------------------------
  `ModuleNotFoundError`               Activate `.venv` and reinstall
                                      dependencies using
                                      `pip install -r requirements.txt`.

  Application fails during startup    Confirm `.env` exists in the
                                      repository root and contains the
                                      required values.

  LLM authentication/model error      Verify `OPENROUTER_API_KEY`,
                                      `OPENROUTER_MODEL`, account access,
                                      and available credits/limits.

  GitHub authentication error         Verify the PAT, required
                                      permissions, and access to the
                                      requested repositories.

  Linear authentication/GraphQL error Verify the API key and the connected
                                      account's workspace access.

  Stored credentials cannot be        Confirm `FERNET_KEY` is the same key
  decrypted                           used when those credentials were
                                      registered.

  Clarification does not resolve the  Use the registered application
  user                                user's name and check that the user
                                      has an active integration for the
                                      requested platform.

  Frontend loads but API calls fail   Check the Uvicorn terminal and
                                      browser developer tools (`F12` →
                                      Console and Network).
  ------------------------------------------------------------------------

Do not share logs containing API keys, authorization headers, or other
secrets.

------------------------------------------------------------------------

## Current Assumptions and Limitations

-   This is a take-home demonstration, not a production deployment.
-   The current GitHub and Linear operations are read-only.
-   GitHub pull-request listing is scoped to pull requests authored by
    the authenticated GitHub account.
-   Linear issue listing is scoped to issues assigned to the
    authenticated Linear account.
-   Provider tool pagination is limited by the current implementation;
    large workspaces may contain more records than one response returns.
-   Conversation checkpointing uses in-memory state. Use a single
    Uvicorn worker for the current setup; restarting the process clears
    in-memory conversation state.
-   The browser UI stores chat sessions/history in browser local
    storage. This is separate from the backend user directory and
    in-memory conversation state.
-   Multiple application users can be registered, but the provider
    credentials connected to each user determine which external data can
    be accessed.

------------------------------------------------------------------------

## Useful Commands

Run from the repository root.

  Task                             Command
  -------------------------------- ---------------------------------------
  Create virtual environment       `python -m venv .venv`
  Activate on Windows PowerShell   `.\.venv\Scripts\Activate.ps1`
  Activate on macOS/Linux          `source .venv/bin/activate`
  Install dependencies             `pip install -r requirements.txt`
  Start application                `uvicorn main:app --reload`
  Generate tree (Windows)          `tree /F /A`
  Generate tree (macOS/Linux)      `tree -a -I '.git|.venv|__pycache__'`
  Run Linear agent test            `python tests/linear_agent_tests.py`

------------------------------------------------------------------------

## Support

When reporting a setup issue, include: 
1. Operating system and Python
version. 
2. The command you ran. 
3. The complete error message with
credentials and sensitive values removed. 
4. The stage where it failed
(installation, startup, user registration, or query).

