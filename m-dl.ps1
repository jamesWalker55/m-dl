Push-Location
Set-Location $PSScriptRoot

uv run m-dl $args

Pop-Location
