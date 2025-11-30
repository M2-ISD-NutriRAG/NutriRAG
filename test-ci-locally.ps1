Write-Host "===================================" -ForegroundColor Cyan
Write-Host "TEST LOCAL DU CI/CD" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# 1. Installation des dependances
Write-Host ""
Write-Host "Installation des dependances..." -ForegroundColor Yellow
pip install -r requirements.txt

# 2. Flake8
Write-Host ""
Write-Host "Linting avec Flake8..." -ForegroundColor Yellow
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics

# 3. Black
Write-Host ""
Write-Host "Verification du formatage avec Black..." -ForegroundColor Yellow
black --check --diff .

# 4. isort
Write-Host ""
Write-Host "Verification des imports avec isort..." -ForegroundColor Yellow
isort --check-only --diff .

# 5. mypy
Write-Host ""
Write-Host "Type checking avec mypy..." -ForegroundColor Yellow
mypy . --ignore-missing-imports --no-strict-optional

# 6. pylint
Write-Host ""
Write-Host "Analyse avec pylint..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Filter *.py | ForEach-Object { pylint $_.FullName }

# 7. pytest
Write-Host ""
Write-Host "Execution des tests..." -ForegroundColor Yellow
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# 8. bandit
Write-Host ""
Write-Host "Verification securite avec bandit..." -ForegroundColor Yellow
pip install bandit
bandit -r . -f json -o bandit-report.json

# 9. safety
Write-Host ""
Write-Host "Verification des dependances avec safety..." -ForegroundColor Yellow
pip install safety
safety check

# 10. radon
Write-Host ""
Write-Host "Analyse de complexite avec radon..." -ForegroundColor Yellow
pip install radon
radon cc . -a -nb
radon mi . -nb

Write-Host ""
Write-Host "===================================" -ForegroundColor Green
Write-Host "TESTS TERMINES" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green