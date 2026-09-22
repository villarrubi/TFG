param(
    [switch]$MemoryOnly,
    [string]$LatexEngine = 'tectonic'
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& python (Join-Path $PSScriptRoot 'build_memory.py') --engine $LatexEngine
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo compilar la memoria LaTeX.'
}
if ($MemoryOnly) { return }
$renderRoot = Join-Path $repoRoot "tmp\rendered_docs"
New-Item -ItemType Directory -Force -Path $renderRoot | Out-Null

$documents = @(
    @{ Name = "Guia_defensa_TFG.docx"; Pdf = (Join-Path $renderRoot "Guia_defensa_TFG.pdf") },
    @{ Name = "Guia_03_Guion_defensa.docx"; Pdf = (Join-Path $renderRoot "Guia_03_Guion_defensa.pdf") },
    @{ Name = "Guia_02_Tecnologias_y_decisiones.docx"; Pdf = (Join-Path $renderRoot "Guia_02_Tecnologias_y_decisiones.pdf") }
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    foreach ($entry in $documents) {
        $docxPath = Join-Path $repoRoot $entry.Name
        $document = $word.Documents.Open($docxPath, $false, $false)
        try {
            $document.Fields.Update() | Out-Null
            foreach ($toc in $document.TablesOfContents) {
                $toc.Update()
            }
            foreach ($index in $document.TablesOfFigures) {
                $index.Update()
            }
            $document.Save()
            if (Test-Path -LiteralPath $entry.Pdf) {
                Remove-Item -LiteralPath $entry.Pdf -Force
            }
            $document.ExportAsFixedFormat($entry.Pdf, 17)
            Write-Output ("Exportado: " + $entry.Pdf)
        }
        finally {
            $document.Close($false)
        }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
}
