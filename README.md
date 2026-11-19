# MCP Security Gateway

A Python-based security gateway that intercepts Model Context Protocol (MCP) tool calls and requires explicit human approval before execution.

The gateway displays an approval popup containing the requested tool and its arguments. The user can choose **Allow** or **Block**. Approved requests are forwarded to the upstream MCP server; blocked or timed-out requests are denied.

## Key Features

- **Human-in-the-loop approval:** Every intercepted tool call requires an explicit decision.
- **Allow / Block controls:** Forward approved calls and prevent blocked calls from executing.
- **Claude Desktop integration:** Connect through a local MCP STDIO server.
- **Claude Web integration:** Connect through an authenticated Streamable HTTP MCP endpoint.
- **Bearer-token authentication:** Protect the HTTP endpoint using a shared secret.
- **Concurrent request handling:** Multiple tool calls can have independent approval popups and decisions.
- **Fail-closed behavior:** Approval timeouts result in denial, never automatic approval.
- **Upstream error handling:** Execution errors are returned as MCP tool errors.
- **Sample MCP server:** Includes `add` and `echo` tools for safe testing.

## Architecture Overview

The project supports two connection modes.

### 1. Claude Desktop – STDIO

Claude Desktop launches the local Python gateway as an MCP server. The gateway connects to the configured upstream MCP server, intercepts tool calls, and waits for approval.

```text
Claude Desktop
      |
      | MCP over STDIO
      v
Python MCP Security Gateway
      |
      +---- Approval Broker
      |          |
      |          v
      |     Tkinter Popup
      |       /      \
      |    Allow     Block
      |      |         |
      v      v         v
  Upstream MCP      MCP denial
     Server          response
```

### 2. Claude Web – Authenticated Streamable HTTP

Claude Web connects to the gateway through an HTTPS endpoint exposed using a tunnel such as ngrok.

```text
Claude Web
    |
    | HTTPS + Bearer Token
    v
HTTPS Tunnel (ngrok)
    |
    v
Authenticated HTTP Gateway
    |
    | MCP Streamable HTTP
    v
Python MCP Security Gateway
    |
    +---- Approval Broker
    |          |
    |          v
    |     Desktop Popup
    |       /      \
    |    Allow     Block
    |      |         |
    v      v         v
  Upstream MCP    MCP denial
     Server        response
```

The local HTTP gateway binds to `127.0.0.1:8000`. The HTTPS tunnel makes the MCP endpoint reachable by Claude Web.

## Technology Stack

- Python 3.12
- MCP Python SDK
- Asyncio
- Tkinter
- Starlette
- Uvicorn
- Streamable HTTP
- Bearer-token authentication
- ngrok (for remote HTTPS tunnelling)
- Pytest

## Project Structure

```text
mcp-security-gateway/
|
+-- app/
|   +-- approval/
|   |   +-- broker.py
|   |
|   +-- config/
|   |   +-- settings.py
|   |
|   +-- proxy/
|   |   +-- mcp_proxy.py
|   |
|   +-- ui/
|   |   +-- popup.py
|   |
|   +-- main.py
|   +-- http_main.py
|   +-- sample_server.py
|   +-- test_client.py
|   +-- concurrent_test_client.py
|   +-- http_test_client.py
|   +-- http_concurrent_test_client.py
|
+-- tests/
+-- config.example.json
+-- config.json
+-- requirements.txt
+-- .gitignore
+-- README.md
```

### Important modules

| Module | Responsibility |
|---|---|
| `app/main.py` | Starts the local STDIO gateway and approval UI |
| `app/http_main.py` | Starts the authenticated HTTP gateway and approval UI |
| `app/proxy/mcp_proxy.py` | Proxies MCP tool discovery and execution over STDIO |
| `app/approval/broker.py` | Coordinates pending requests and approval decisions across threads |
| `app/ui/popup.py` | Displays Allow/Block approval popups |
| `app/config/settings.py` | Loads and validates gateway configuration |
| `app/sample_server.py` | Provides safe sample tools |
| `app/concurrent_test_client.py` | Tests concurrent STDIO tool calls |
| `app/http_concurrent_test_client.py` | Tests concurrent HTTP tool calls |

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer (Python 3.12 is recommended)
- Git
- Claude Desktop for local integration
- Claude Web account with custom MCP connector support for remote integration
- ngrok or an equivalent HTTPS tunnel for Claude Web testing

## Installation

Clone the repository:

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd mcp-security-gateway
```

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the local configuration:

```powershell
Copy-Item config.example.json config.json
```

The default example configuration is:

```json
{
  "upstream_command": "python",
  "upstream_args": ["-m", "app.sample_server"],
  "approval_timeout_seconds": 120
}
```

If Python is not available through PATH, configure `upstream_command` with the full path to the Python executable in your virtual environment.

## Running the STDIO Gateway

Start the local gateway:

```powershell
python -m app.main
```

The gateway starts the upstream sample MCP server and waits for tool requests from an MCP client.

### Local smoke test

Open a second PowerShell terminal, activate the virtual environment, and run:

```powershell
python -m app.test_client --tool add
```

The approval popup displays the `add` tool request.

- Select **Allow** to execute the upstream tool.
- Select **Block** to prevent execution.

The sample call uses:

```text
add(4, 5)
```

Expected approved result:

```text
9
```

Test the echo tool:

```powershell
python -m app.test_client --tool echo
```

## Claude Desktop Integration

Add the gateway as a local MCP server in Claude Desktop's MCP configuration.

Example configuration:

```json
{
  "mcpServers": {
    "mcp-security-gateway": {
      "command": "C:\\path\\to\\mcp-security-gateway\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.main"],
      "cwd": "C:\\path\\to\\mcp-security-gateway",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\mcp-security-gateway"
      }
    }
  }
}
```

Replace the example paths with the actual project location.

Restart Claude Desktop after saving the configuration.

When Claude requests an exposed tool, the gateway displays an approval popup. The upstream tool executes only after the user selects Allow.

## Running the Authenticated HTTP Gateway

The HTTP gateway provides a Streamable HTTP MCP endpoint for remote MCP clients.

It requires a bearer token supplied through an environment variable.

Generate a secure token in PowerShell:

```powershell
$env:MCP_GATEWAY_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start the HTTP gateway:

```powershell
python -m app.http_main
```

The local MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

The HTTP gateway rejects requests with a missing or invalid bearer token using HTTP 401.

### Test the HTTP gateway

Open another PowerShell terminal.

Set the same token in that terminal (use the token generated in the gateway terminal):

```powershell
$env:MCP_GATEWAY_TOKEN = "<YOUR_GATEWAY_TOKEN>"
```

Run:

```powershell
python -m app.http_test_client
```

An approval popup appears for the `add` tool call.

Expected approved result:

```text
40
```

### Expose the HTTP endpoint using ngrok

Start an HTTPS tunnel in a separate terminal:

```powershell
ngrok http 8000
```

Use the HTTPS forwarding address displayed by ngrok, with `/mcp` appended.

Example:

```text
https://your-ngrok-domain.ngrok-free.dev/mcp
```

Keep both the Python HTTP gateway and ngrok running while testing.

### Configure Claude Web

Create a custom MCP connector in Claude Web with:

- **Server URL:** Your HTTPS tunnel URL ending in `/mcp`
- **Authentication:** No sign-in, when using the custom request-header configuration
- **Request header name:** `Authorization`
- **Request header value:** `Bearer <YOUR_GATEWAY_TOKEN>`

The bearer token must match the `MCP_GATEWAY_TOKEN` configured in the gateway process.

Never publish the token or commit it to GitHub.

## Concurrency Testing

The gateway supports multiple independent tool requests.

### STDIO concurrency test

```powershell
python -m app.concurrent_test_client
```

### HTTP concurrency test

```powershell
python -m app.http_concurrent_test_client
```

Each request receives its own approval popup and can be independently allowed or blocked.

The approval broker uses:

- A thread-safe queue for communication with the UI.
- An asyncio Future for each pending request.
- `loop.call_soon_threadsafe()` to safely resolve requests from the UI thread.
- Unique request IDs to distinguish simultaneous approvals.

## Security Design

### Bearer-token authentication

The HTTP gateway protects the `/mcp` endpoint using a bearer token.

Token comparison uses `hmac.compare_digest()` to avoid ordinary string-comparison timing differences.

### Human approval

Every intercepted tool call is paused until the user makes an explicit decision.

### Fail-closed timeout

If no decision is received within the configured timeout, the request is denied.

### Block behavior

Blocked requests return an MCP error result without forwarding the tool call to the upstream server.

### Credential handling

- Do not hardcode authentication tokens in source code.
- Do not commit actual tokens or credentials.
- Keep local secrets in environment variables.
- Do not publish ngrok authentication tokens.

## Testing Performed

The following scenarios were tested during development:

| Test scenario | Expected behavior | Result |
|---|---|---|
| STDIO tool discovery | Expose upstream tools | Passed |
| STDIO Allow | Forward the approved call | Passed |
| STDIO Block | Prevent upstream execution | Passed |
| Concurrent STDIO requests | Independent approval decisions | Passed |
| HTTP tool discovery | Expose tools over Streamable HTTP | Passed |
| HTTP Allow | Forward the approved call | Passed |
| HTTP Block | Deny the call | Passed |
| Concurrent HTTP requests | Independent approval decisions | Passed |
| Bearer authentication | Reject invalid or missing token | Passed |
| Claude Desktop integration | Approval-controlled tool execution | Passed |
| Claude Web integration | Approval-controlled tool execution | Passed |

## Current Scope and Limitations

- The gateway controls tool calls routed through it. Direct connections to other MCP servers are outside its control.
- The current implementation proxies tool discovery and tool execution. It does not proxy every MCP capability, such as resources, prompts, sampling, and notifications.
- The HTTP gateway currently binds to localhost and relies on an HTTPS tunnel for remote access.
- The desktop approval UI must remain running while approvals are required.
- The current prototype is intended for assessment and demonstration, not production deployment.
- Production deployment would require stronger lifecycle management, secret rotation, audit logging, argument redaction, and a hardened remote-to-desktop approval architecture.

## Future Enhancements

- Windows system-tray/background operation.
- Graceful shutdown and recovery.
- Persistent audit logs for approval decisions.
- Sensitive argument masking.
- Configurable per-tool approval policies.
- Production-grade remote authentication and desktop-agent communication.
- Automated unit and integration test coverage.

## License

Assessment prototype. A suitable open-source license can be added before public distribution.



## Demo Video

[Watch MCP Security Gateway Demo](https://drive.google.com/file/d/1e5MCPSeYIJtC45NiKQwdHQQvTYRpKWL1/view?usp=sharing)