Push-Location
Set-Location $PSScriptRoot

poetry run m-dl $args

Pop-Location
