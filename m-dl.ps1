Push-Location
Set-Location $PSScriptRoot

rye run m-dl $args

Pop-Location
