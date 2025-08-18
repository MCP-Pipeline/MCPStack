# Security Policy

We take security seriously and encourage responsible disclosure.

If you believe you’ve found a security vulnerability in **MCPStack-Tool**, please report it to us privately rather than opening a public issue.

## Reporting a Vulnerability

Include the following information in your report:

- **Project**: <Repository URL> (e.g., From `https://github.com/MCP-Pipeline/MCPStack-Tool`)
- **Public**: Has this issue already been disclosed elsewhere?
- **Description**: A clear explanation of the vulnerability, with reproduction steps if possible.
- **Environment**: Operating system, Python version, MCP client, and any relevant setup details.

Send reports to: **simon.gilbert.provost@gmail.com** 

We will acknowledge receipt within 7 days and aim to provide a resolution or mitigation timeline within 30 days. Please do not share vulnerabilities publicly until a fix has been released.

## Scope and Considerations

- **Tool Combinations**: MCPStack is designed to compose with other MCP tools. Unexpected or unsafe interactions between tools cannot be predicted or prevented at the MCPStack-Tool level. The responsibility for safe orchestration rests with the user.  
- **Data Breach Risks**: MCPStack runs locally and does not send data to external services. There are no cloud communications by default, so conventional remote data breaches do not apply.  
- **GitHub Issues and Pull Requests**: Do not upload sensitive data (such as private datasets, logs, or credentials) when filing issues or submitting pull requests. Use synthetic or anonymized examples instead.

## Good Practices

- Keep dependencies updated.  
- Test tool compositions in a controlled environment.  
- Sanitize any shared examples when discussing issues publicly.