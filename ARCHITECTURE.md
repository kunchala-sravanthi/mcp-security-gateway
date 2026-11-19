# MCP Security Gateway — Architecture

## 1. Overview

The MCP Security Gateway is a Python-based middleware application that intercepts Model Context Protocol (MCP) tool calls and requires explicit human approval before forwarding them to an upstream MCP server.

It supports two connection methods:

- **STDIO transport:** Integrates with Claude Desktop.
- **Streamable HTTP transport:** Integrates with Claude Web through a secure bearer-token-protected endpoint.

The gateway follows a human-in-the-loop security model: tool execution is allowed only after the user selects **Allow**.

## 2. High-Level Architecture

### Claude Desktop — STDIO

```text
Claude Desktop
      |
      | MCP over STDIO
      v
MCP Security Gateway
      |
      v
Tool Call Interceptor
      |
      v
Approval Broker
      |
      v
Tkinter Approval Popup
      |
      +---- Allow ----> Upstream MCP Server
      |                       |
      |                       v
      |                  Tool Execution
      |                       |
      |<----------------------+
      |
      +---- Block ----> Return denial response
```

### Claude Web — Streamable HTTP

```text
Claude Web
    |
    | HTTPS + Bearer Token
    v
ngrok Public Tunnel
    |
    v
Local HTTP Gateway
    |
    v
Bearer Token Middleware
    |
    v
MCP Tool Call Interceptor
    |
    v
Approval Broker
    |
    v
Tkinter Approval Popup
    |
    +---- Allow ----> Upstream MCP Server
    |
    +---- Block ----> Return denial response
```

## 3. Main Components

### 3.1 Application Entry Point

**Files:** `app/main.py`, `app/http_main.py`

These modules initialize the application, load configuration, create the approval broker, start the MCP server, and launch the approval UI.

The STDIO and HTTP transports have separate entry points.

### 3.2 MCP Proxy

**File:** `app/proxy/mcp_proxy.py`

Responsibilities:

- Connect to the configured upstream MCP server.
- Discover available tools.
- Expose upstream tools through the gateway.
- Intercept incoming tool execution requests.
- Request human approval before forwarding.
- Return tool results or denial responses.

### 3.3 Approval Broker

**File:** `app/approval/broker.py`

The approval broker coordinates communication between asynchronous MCP requests and the Tkinter user interface.

Responsibilities:

- Generate a unique ID for every approval request.
- Maintain pending approval requests.
- Handle multiple simultaneous requests independently.
- Wait asynchronously for the user's decision.
- Apply an approval timeout.
- Deny unresolved requests when the timeout expires.
- Resolve pending requests safely.

Each approval request has its own asynchronous future, allowing independent decisions for concurrent tool calls.

### 3.4 Approval User Interface

**File:** `app/ui/popup.py`

The application uses Tkinter to display confirmation dialogs.

Each popup displays the requested tool and its arguments.

The user can:

- **Allow:** Forward the request to the upstream MCP server.
- **Block:** Prevent execution and return a denial response.
- **Close the popup:** Treat the request as denied.

The popup is configured to stay on top of other windows.

### 3.5 HTTP Authentication Middleware

**File:** `app/http_main.py`

The HTTP gateway protects the MCP endpoint using bearer-token authentication.

Security features:

- Requires an Authorization header.
- Validates the Bearer token.
- Uses constant-time token comparison.
- Rejects missing or invalid credentials with HTTP 401.
- Reads the token from the `MCP_GATEWAY_TOKEN` environment variable.

The token is not stored in the source code.

### 3.6 Configuration

**Files:** `config.example.json`, `app/config/settings.py`

The application reads its upstream server command, arguments, and approval timeout from configuration.

The local `config.json` file contains machine-specific settings and is excluded from Git.

## 4. Tool Request Lifecycle

1. Claude requests execution of an MCP tool.
2. The gateway receives the request.
3. The gateway creates a unique approval request.
4. The approval broker sends the request to the UI.
5. A confirmation popup appears.
6. The user selects Allow or Block.
7. If allowed, the gateway forwards the request upstream.
8. The upstream MCP server executes the tool.
9. The result is returned to Claude.
10. If blocked or timed out, the gateway returns a denial response without executing the upstream tool.

## 5. Concurrency Handling

The gateway supports multiple simultaneous tool requests.

Each request is tracked using a unique request ID and an independent asynchronous future.

The approval broker uses a thread-safe queue to communicate with the Tkinter UI.

This design ensures that:

- Multiple approval popups can be displayed.
- Each request receives its own decision.
- Approving one request does not automatically approve another.
- Blocking one request does not affect other pending requests.

## 6. Error Handling and Fail-Safe Behaviour

The gateway uses a fail-closed approach for approval decisions.

- Approval timeout results in denial.
- Closing a popup results in denial.
- Closing the application denies pending requests.
- Invalid HTTP authentication is rejected.
- Upstream tool execution exceptions are logged and returned as error responses.

A tool is never intentionally forwarded before approval.

## 7. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| MCP integration | MCP Python SDK |
| User interface | Tkinter |
| Async processing | asyncio |
| HTTP server | Uvicorn |
| HTTP framework | Starlette |
| Authentication | Bearer Token |
| Public tunnel | ngrok |
| Testing | pytest |
| Version control | Git and GitHub |

## 8. Testing and Validation

The implementation was validated using:

- Local STDIO MCP client.
- Local Streamable HTTP MCP client.
- Claude Desktop integration.
- Claude Web integration.
- Allow and Block approval scenarios.
- Approval timeout behaviour.
- Concurrent tool requests.
- Bearer-token authentication.
- Automated pytest tests.

The automated test suite currently reports **2 passed tests**.

## 9. Security Considerations

- Human approval is required before tool execution.
- HTTP requests require bearer-token authentication.
- Secrets are supplied through environment variables.
- Local configuration and virtual environments are excluded from Git.
- Approval timeouts prevent requests from remaining pending indefinitely.
- Blocked requests are not forwarded to the upstream server.

## 10. Limitations and Future Improvements

Potential improvements include:

- OAuth-based authentication.
- Persistent audit logging.
- Approval history and reporting.
- Configurable per-tool security policies.
- Packaging the gateway as a Windows background application.
- Additional automated integration and security tests.

## 11. Conclusion

The MCP Security Gateway provides a human-in-the-loop security layer for MCP tool execution. It supports Claude Desktop and Claude Web, handles concurrent requests, enforces approval decisions, and protects HTTP access using bearer-token authentication.