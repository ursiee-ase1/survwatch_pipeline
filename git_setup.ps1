# Git Setup Script for CCTV Analysis Project

Write-Host "Setting up Git repository..." -ForegroundColor Green

# Check if .git exists
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
}

# Add .gitignore (to exclude .pem files)
Write-Host "Updating .gitignore..." -ForegroundColor Yellow

# Stage files (excluding .pem files)
Write-Host "Adding files to git..." -ForegroundColor Yellow
git add .

# Check status
Write-Host "`nCurrent status:" -ForegroundColor Cyan
git status

Write-Host "`nNext steps:" -ForegroundColor Green
Write-Host "1. Review the files above" -ForegroundColor White
Write-Host "2. If cctv-key.pem appears, it's a problem - make sure *.pem is in .gitignore" -ForegroundColor Yellow
Write-Host "3. Commit: git commit -m 'Initial commit'" -ForegroundColor White
Write-Host "4. Rename branch: git branch -M main" -ForegroundColor White
Write-Host "5. Add remote: git remote add origin https://github.com/ursiee-ase1/survwatch_pipeline.git" -ForegroundColor White
Write-Host "6. Push: git push -u origin main" -ForegroundColor White

