<#
Uninstall-HackathonTools.ps1
Versão 3 - compatível com Intune (system context)
#>

$ErrorActionPreference = "SilentlyContinue"

function Log($msg) { Write-Host $msg }

Log "=== Remoção das Ferramentas Hackathon (Node.js, VS Code, Claude CLI) ==="

# 1. Desinstalar Claude CLI (npm global)
try {
    Log "Removendo Claude CLI..."
    Start-Process "npm" -ArgumentList "uninstall -g @anthropic-ai/claude-code --force --no-audit --no-fund" -Wait -NoNewWindow
    Remove-Item "C:\Program Files\nodejs\claude.cmd" -Force -ErrorAction SilentlyContinue
    Remove-Item "C:\Program Files\nodejs\node_modules\@anthropic-ai" -Recurse -Force -ErrorAction SilentlyContinue
    Log "Claude CLI removido."
} catch {
    Log "Aviso: Claude CLI pode já não estar presente."
}

# 2. Desinstalar Visual Studio Code
try {
    Log "Removendo Visual Studio Code..."
    choco uninstall vscode -y --no-progress
    Log "VS Code removido."
} catch {
    Log "Aviso: VS Code pode já não estar presente."
}

# 3. Desinstalar Node.js
try {
    Log "Removendo Node.js..."
    choco uninstall nodejs-lts -y --no-progress
    Log "Node.js removido."
} catch {
    Log "Aviso: Node.js pode já não estar presente."
}

# 4. Desinstalar Git (se foi instalado pelo script)
try {
    Log "Removendo Git..."
    choco uninstall git -y --no-progress
    Log "Git removido."
} catch {
    Log "Aviso: Git pode já não estar presente."
}

# 5. Limpar variáveis de ambiente
$envVars = @(
    "CLAUDE_CODE_USE_BEDROCK",
    "DISABLE_PROMPT_CACHING",
    "AWS_REGION",
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_GIT_BASH_PATH"
)

foreach ($v in $envVars) {
    try {
        [Environment]::SetEnvironmentVariable($v, $null, [EnvironmentVariableTarget]::Machine)
        Log "Variável $v removida."
    } catch {
        Log "Aviso: Falha ao remover variável $v."
    }
}

# 6. Limpar pastas residuais
try {
    Remove-Item "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Studio Code" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$env:APPDATA\npm\claude*" -Force -ErrorAction SilentlyContinue
    Remove-Item "C:\ProgramData\SecilHackathon" -Recurse -Force -ErrorAction SilentlyContinue
    Log "Pastas temporárias limpas."
} catch {
    Log "Aviso: Algumas pastas não puderam ser removidas."
}

Log "=== Desinstalação concluída com sucesso ==="
exit 0
