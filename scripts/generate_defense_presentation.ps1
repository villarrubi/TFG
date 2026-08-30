Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Output = Join-Path $Root "Presentacion_defensa_TFG.pptx"
$QaDir = Join-Path $Root "_docx_qa\pptx_final"

function Get-Color([string]$Hex) {
    $value = $Hex.TrimStart('#')
    $r = [Convert]::ToInt32($value.Substring(0, 2), 16)
    $g = [Convert]::ToInt32($value.Substring(2, 2), 16)
    $b = [Convert]::ToInt32($value.Substring(4, 2), 16)
    return $r + (256 * $g) + (65536 * $b)
}

$C = @{
    Ink = Get-Color "07131F"
    Ink2 = Get-Color "0B1F33"
    Ink3 = Get-Color "12304A"
    Muted = Get-Color "49657A"
    Soft = Get-Color "6A8192"
    Canvas = Get-Color "F4F7F9"
    White = Get-Color "FFFFFF"
    Line = Get-Color "DCE5EA"
    Panel = Get-Color "EAF0F3"
    Teal = Get-Color "0D9488"
    TealDark = Get-Color "0F766E"
    TealLight = Get-Color "CCFBF1"
    Cyan = Get-Color "38BDF8"
    Blue = Get-Color "3D8DFF"
    Orange = Get-Color "D97706"
    Red = Get-Color "B42318"
}

function Add-Text {
    param(
        $Slide,
        [string]$Text,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [double]$Size = 18,
        [int]$Color = $C.Ink,
        [bool]$Bold = $false,
        [int]$Align = 1,
        [int]$Vertical = 1,
        [string]$Name = "Text"
    )
    $shape = $Slide.Shapes.AddTextbox(1, $Left, $Top, $Width, $Height)
    $shape.Name = $Name
    $shape.TextFrame.MarginLeft = 0
    $shape.TextFrame.MarginRight = 0
    $shape.TextFrame.MarginTop = 0
    $shape.TextFrame.MarginBottom = 0
    $shape.TextFrame.WordWrap = -1
    $shape.TextFrame.AutoSize = 0
    $shape.TextFrame.VerticalAnchor = $Vertical
    $range = $shape.TextFrame.TextRange
    $range.Text = $Text
    $range.Font.Name = "Arial"
    $range.Font.Size = $Size
    $range.Font.Bold = $(if ($Bold) { -1 } else { 0 })
    $range.Font.Color.RGB = $Color
    $range.ParagraphFormat.Alignment = $Align
    $range.ParagraphFormat.SpaceAfter = 4
    return $shape
}

function Add-Rect {
    param(
        $Slide,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [int]$Fill,
        [int]$Line = -1,
        [double]$Radius = 0,
        [string]$Name = "Shape"
    )
    $geometry = if ($Radius -gt 0) { 5 } else { 1 }
    $shape = $Slide.Shapes.AddShape($geometry, $Left, $Top, $Width, $Height)
    $shape.Name = $Name
    $shape.Fill.Visible = -1
    $shape.Fill.Solid()
    $shape.Fill.ForeColor.RGB = $Fill
    if ($Line -ge 0) {
        $shape.Line.Visible = -1
        $shape.Line.ForeColor.RGB = $Line
        $shape.Line.Weight = 1
    }
    else {
        $shape.Line.Visible = 0
    }
    return $shape
}

function Add-Line {
    param(
        $Slide,
        [double]$X1,
        [double]$Y1,
        [double]$X2,
        [double]$Y2,
        [int]$Color = $C.Line,
        [double]$Weight = 1.5,
        [bool]$Arrow = $false,
        [string]$Name = "Line"
    )
    $line = $Slide.Shapes.AddLine($X1, $Y1, $X2, $Y2)
    $line.Name = $Name
    $line.Line.ForeColor.RGB = $Color
    $line.Line.Weight = $Weight
    if ($Arrow) { $line.Line.EndArrowheadStyle = 3 }
    return $line
}

function Add-Circle {
    param($Slide, [double]$Left, [double]$Top, [double]$Size, [int]$Fill, [string]$Name)
    $shape = $Slide.Shapes.AddShape(9, $Left, $Top, $Size, $Size)
    $shape.Name = $Name
    $shape.Fill.Solid()
    $shape.Fill.ForeColor.RGB = $Fill
    $shape.Line.Visible = 0
    return $shape
}

function New-Slide {
    param($Presentation, [int]$Background = $C.Canvas)
    $slide = $Presentation.Slides.Add($Presentation.Slides.Count + 1, 12)
    $slide.FollowMasterBackground = 0
    $slide.Background.Fill.Solid()
    $slide.Background.Fill.ForeColor.RGB = $Background
    return $slide
}

function Add-Header {
    param($Slide, [string]$Section, [string]$Title, [int]$Number)
    [void](Add-Text $Slide $Section.ToUpperInvariant() 56 20 360 16 10 $C.TealDark $true 1 1 "Section")
    [void](Add-Text $Slide $Title 56 42 848 50 35 $C.Ink $true 1 1 "Slide title")
    [void](Add-Line $Slide 56 101 112 101 $C.Teal 4 $false "Accent rule")
    [void](Add-Text $Slide "Alejandro Villarrubia García · TFG" 56 512 300 12 9 $C.Soft $false 1 1 "Footer author")
    [void](Add-Text $Slide ([string]$Number) 882 510 22 14 10 $C.Soft $true 2 1 "Slide number")
}

function Add-Notes {
    param($Slide, [string]$Text)
    $notes = $Slide.NotesPage
    for ($i = 1; $i -le $notes.Shapes.Count; $i++) {
        $shape = $notes.Shapes.Item($i)
        if ($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2) {
            $shape.TextFrame.TextRange.Text = $Text
            return
        }
    }
    throw "No se encontró el marcador de notas en la diapositiva $($Slide.SlideIndex)."
}

function Add-Node {
    param(
        $Slide,
        [string]$Title,
        [string]$Body,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [int]$Fill = $C.White,
        [int]$TextColor = $C.Ink,
        [int]$Border = $C.Line,
        [string]$Name = "Node"
    )
    [void](Add-Rect $Slide $Left $Top $Width $Height $Fill $Border 1 $Name)
    [void](Add-Text $Slide $Title ($Left + 14) ($Top + 12) ($Width - 28) 24 17 $TextColor $true 1 1 "$Name title")
    [void](Add-Text $Slide $Body ($Left + 14) ($Top + 39) ($Width - 28) ($Height - 48) 12 $TextColor $false 1 1 "$Name body")
}

$powerPoint = $null
$presentation = $null
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $powerPoint.Visible = -1
    $presentation = $powerPoint.Presentations.Add()
    $presentation.PageSetup.SlideWidth = 960
    $presentation.PageSetup.SlideHeight = 540

    # 1. Portada
    $s = New-Slide $presentation $C.Ink
    [void](Add-Rect $s 728 0 232 540 $C.Ink3 -1 0 "Accent field")
    [void](Add-Line $s 760 94 900 94 $C.Teal 5 $false "Cover accent")
    [void](Add-Line $s 760 118 870 118 $C.Cyan 2 $false "Cover secondary accent")
    [void](Add-Text $s "TRABAJO FIN DE GRADO · 2026" 58 50 420 22 12 $C.TealLight $true 1 1 "Eyebrow")
    [void](Add-Text $s "Detección de phishing`nen correos electrónicos" 58 138 640 142 50 $C.White $true 1 1 "Deck title")
    [void](Add-Text $s "Sistema cliente-servidor con análisis explicable y modelos centralizados" 58 304 590 58 21 (Get-Color "C9D7E0") $false 1 1 "Subtitle")
    [void](Add-Text $s "Alejandro Villarrubia García" 58 430 380 24 16 $C.White $true 1 1 "Author")
    [void](Add-Text $s "Tutor: Carmelo González García · UEMC" 58 460 420 18 12 (Get-Color "A9BBC8") $false 1 1 "Tutor")
    [void](Add-Text $s "TFG" 768 400 150 58 38 $C.White $true 2 3 "Cover mark")
    Add-Notes $s "Apertura: presentar el problema y la aportación en dos frases. El sistema combina señales explicables y aprendizaje supervisado, pero la decisión se centraliza en un único servidor.`n`n[Sources]`n- TFG.txt: portada y resumen.`n[/Sources]"

    # 2. Problema
    $s = New-Slide $presentation
    Add-Header $s "Motivación" "El problema exige una decisión explicable" 2
    [void](Add-Rect $s 56 132 302 322 $C.Ink -1 0 "Question field")
    [void](Add-Text $s "¿Cómo detectar phishing sin perder la explicación?" 82 170 250 176 32 $C.White $true 1 1 "Question")
    [void](Add-Text $s "Una etiqueta aislada no basta para revisar un correo sospechoso." 82 365 240 60 15 (Get-Color "C9D7E0") $false 1 1 "Question support")
    $items = @(
        @("01", "Señales técnicas", "Resultados SPF, DKIM y DMARC presentes en cabeceras, dominios, URLs, HTML y adjuntos."),
        @("02", "Ingeniería social", "Urgencia, autoridad, credenciales y patrones BEC."),
        @("03", "Decisión trazable", "Riesgo, señales activadas y explicación para el usuario.")
    )
    $y = 142
    foreach ($item in $items) {
        [void](Add-Text $s $item[0] 410 $y 42 22 12 $C.TealDark $true 1 1 "Index $($item[0])")
        [void](Add-Text $s $item[1] 468 $y 330 26 21 $C.Ink $true 1 1 "Problem $($item[0])")
        [void](Add-Text $s $item[2] 468 ($y + 34) 390 48 15 $C.Muted $false 1 1 "Problem detail $($item[0])")
        if ($y -lt 330) { [void](Add-Line $s 410 ($y + 91) 870 ($y + 91) $C.Line 1 $false "Problem divider") }
        $y += 108
    }
    Add-Notes $s "Explicar que el phishing combina aspectos técnicos y humanos. La propuesta no devuelve solo una clase: muestra evidencias que permiten revisar la decisión.`n`n[Sources]`n- TFG.txt: introducción, señales analizadas y diseño de la aplicación.`n[/Sources]"

    # 3. Objetivos
    $s = New-Slide $presentation
    Add-Header $s "Objetivos" "Un backend central cumple cuatro objetivos" 3
    [void](Add-Text $s "Una única lógica de análisis; varias formas de usarla." 56 128 520 42 25 $C.Ink3 $true 1 1 "Thesis")
    [void](Add-Text $s "El cliente recoge datos y presenta resultados. El servidor concentra parser, detectores, entrenamiento y versiones." 56 181 500 74 17 $C.Muted $false 1 1 "Thesis detail")
    $objectives = @(
        @("01", "Aceptar varias entradas", "Texto, EML, Gmail, extensión y monitor."),
        @("02", "Combinar dos enfoques", "Heurística explicable + TF-IDF y MLP bilingüe."),
        @("03", "Compartir los modelos", "Una versión activa ES/EN para todos los clientes."),
        @("04", "Evaluar con trazabilidad", "Calibración separada, EML reservados y pruebas reproducibles.")
    )
    $y = 124
    foreach ($o in $objectives) {
        [void](Add-Text $s $o[0] 620 $y 46 28 14 $C.TealDark $true 1 1 "Objective index")
        [void](Add-Text $s $o[1] 684 $y 220 26 18 $C.Ink $true 1 1 "Objective")
        [void](Add-Text $s $o[2] 684 ($y + 30) 220 45 13 $C.Muted $false 1 1 "Objective detail")
        if ($y -lt 390) { [void](Add-Line $s 620 ($y + 82) 904 ($y + 82) $C.Line 1 $false "Objective divider") }
        $y += 92
    }
    Add-Notes $s "Presentar los objetivos como decisiones de diseño. La centralización permite que una actualización del servidor llegue a todos los clientes sin distribuir modelos.`n`n[Sources]`n- TFG.txt: objetivos y resumen de arquitectura.`n- README.md: Cómo está montado.`n[/Sources]"

    # 4. Arquitectura
    $s = New-Slide $presentation
    Add-Header $s "Arquitectura" "Sí: es una arquitectura cliente-servidor" 4
    # Conectores primero, para quedar detrás de los nodos.
    [void](Add-Line $s 195 196 195 207 $C.Muted 1.5 $true "Browser to web")
    [void](Add-Line $s 286 251 520 251 $C.TealDark 2.3 $true "Web to backend")
    [void](Add-Line $s 286 338 520 303 $C.TealDark 2.3 $true "Extension to backend")
    [void](Add-Line $s 286 425 520 355 $C.TealDark 2.3 $true "Monitor to backend")
    Add-Node $s "Navegador" "Interfaz visible" 108 132 174 64 $C.Panel $C.Ink $C.Line "Browser"
    Add-Node $s "Streamlit" "Presentación y cliente HTTP" 96 207 190 72 $C.White $C.Ink $C.Teal "Streamlit"
    Add-Node $s "Extensión Gmail" "Correo visible → /analyze" 96 302 190 72 $C.White $C.Ink $C.Line "Extension"
    Add-Node $s "Monitor Gmail" "Lote + alerta Telegram" 96 397 190 72 $C.White $C.Ink $C.Line "Monitor"
    [void](Add-Rect $s 520 158 346 292 $C.Ink -1 1 "Backend central")
    [void](Add-Text $s "BACKEND CENTRAL · :8766" 548 181 282 28 20 $C.TealLight $true 1 1 "Backend title")
    [void](Add-Text $s "• Parser MIME / EML`n• Señales heurísticas`n• Modelo neuronal ES activo`n• Modelo neuronal EN activo`n• Entrenamiento y versionado" 548 229 270 156 16 $C.White $false 1 1 "Backend contents")
    [void](Add-Text $s "HTTP / JSON" 388 222 92 18 11 $C.TealDark $true 2 1 "Protocol")
    [void](Add-Text $s "En la defensa ambos procesos pueden estar en el mismo equipo; siguen separados por un contrato HTTP." 520 462 346 38 13 $C.Muted $false 1 1 "Architecture note")
    Add-Notes $s "Esta es la diapositiva clave. El navegador habla con Streamlit y Streamlit con el backend; la extensión y el monitor llaman a la misma API. Local describe la ubicación, no elimina la separación cliente-servidor.`n`n[Sources]`n- README.md: Cómo está montado y Componentes.`n- TFG.txt: Arquitectura general.`n[/Sources]"

    # 5. Flujo
    $s = New-Slide $presentation
    Add-Header $s "Funcionamiento" "Cada correo sigue un flujo único y trazable" 5
    $xs = @(74, 244, 414, 584, 754)
    for ($i = 0; $i -lt 4; $i++) { [void](Add-Line $s ($xs[$i] + 126) 269 ($xs[$i + 1] - 10) 269 $C.Teal 2 $true "Flow arrow $i") }
    $steps = @(
        @("01", "Entrada", "Texto, EML o campos JSON"),
        @("02", "Normalización", "Cabeceras, HTML, enlaces y adjuntos"),
        @("03", "Detección", "Heurística + modelo por idioma"),
        @("04", "Fusión", "Pesos, umbral y alta confianza"),
        @("05", "Respuesta", "Riesgo, señales y explicación")
    )
    for ($i = 0; $i -lt $steps.Count; $i++) {
        [void](Add-Circle $s $xs[$i] 248 42 $(if ($i -eq 4) { $C.Teal } else { $C.Ink }) "Flow node $i")
        [void](Add-Text $s $steps[$i][0] ($xs[$i] + 7) 259 28 16 10 $C.White $true 2 1 "Flow number")
        [void](Add-Text $s $steps[$i][1] ($xs[$i] - 10) 314 132 26 17 $C.Ink $true 2 1 "Flow title")
        [void](Add-Text $s $steps[$i][2] ($xs[$i] - 16) 350 144 58 12 $C.Muted $false 2 1 "Flow detail")
    }
    [void](Add-Text $s "El contrato /analyze limita la entrada, devuelve una respuesta común y mantiene la lógica fuera de los clientes." 140 440 680 38 15 $C.Ink3 $true 2 1 "Flow takeaway")
    Add-Notes $s "Recorrer el correo de izquierda a derecha. Todas las entradas terminan en la misma representación y todos los clientes reciben el mismo formato de salida.`n`n[Sources]`n- TFG.txt: Flujo de análisis y contrato del backend.`n- README.md: Contrato del backend.`n[/Sources]"

    # 6. Detectores
    $s = New-Slide $presentation
    Add-Header $s "Método" "Dos detectores aportan señales complementarias" 6
    [void](Add-Text $s "HEURÍSTICA EXPLICABLE" 72 137 360 22 12 $C.TealDark $true 1 1 "Heuristic label")
    [void](Add-Text $s "Inspecciona indicios concretos" 72 170 360 34 24 $C.Ink $true 1 1 "Heuristic title")
    [void](Add-Text $s "Lectura pasiva de SPF/DKIM/DMARC en cabeceras`nRemitente, dominio y URLs`nHTML, adjuntos y redirecciones`nUrgencia, credenciales y BEC" 72 225 360 140 16 $C.Muted $false 1 1 "Heuristic list")
    [void](Add-Line $s 480 136 480 390 $C.Line 1.4 $false "Detector divider")
    [void](Add-Text $s "CLASIFICADOR NEURONAL" 528 137 360 22 12 $C.Blue $true 1 1 "Neural label")
    [void](Add-Text $s "Aprende patrones del lenguaje" 528 170 360 34 24 $C.Ink $true 1 1 "Neural title")
    [void](Add-Text $s "TF-IDF con n-gramas`nPerceptrón multicapa (MLP)`nModelos separados ES / EN`nProbabilidad de phishing" 528 225 360 140 16 $C.Muted $false 1 1 "Neural list")
    [void](Add-Rect $s 124 410 712 62 $C.Ink -1 0 "Combined band")
    [void](Add-Text $s "MODO COMBINADO" 148 430 150 18 12 $C.TealLight $true 1 1 "Combined label")
    [void](Add-Text $s "45/55 · umbral 21 · alta confianza ≥ 70" 318 425 490 28 18 $C.White $true 1 3 "Combined formula")
    Add-Notes $s "Contrastar interpretabilidad y capacidad de generalización. El modo combinado fue calibrado con un conjunto separado; la evidencia individual fuerte no se diluye en la media.`n`n[Sources]`n- TFG.txt: Diseño del clasificador y metodología cuantitativa.`n- evaluation/calibration_results.json.`n[/Sources]"

    # 7. Modelos centrales
    $s = New-Slide $presentation
    Add-Header $s "Centralización" "Una versión activa sirve a todos los clientes" 7
    [void](Add-Line $s 98 272 862 272 $C.Ink 1.5 $false "Model timeline")
    $timelineX = @(128, 420, 712)
    foreach ($x in $timelineX) { [void](Add-Circle $s ($x - 7) 265 14 $C.Teal "Timeline dot") }
    $timeline = @(
        @("01 · ENTRENAR", "El cliente envía CSV e hiperparámetros", "El backend crea un pipeline nuevo desde cero."),
        @("02 · ACTIVAR", "Guardado atómico y caché invalidada", "Una versión activa por idioma: ES y EN."),
        @("03 · COMPARTIR", "Web, extensión y monitor", "La siguiente petición usa la versión nueva.")
    )
    for ($i = 0; $i -lt 3; $i++) {
        $x = $timelineX[$i] - 42
        [void](Add-Text $s $timeline[$i][0] $x 204 240 20 12 $C.TealDark $true 1 1 "Timeline label")
        [void](Add-Text $s $timeline[$i][1] $x 312 240 54 18 $C.Ink $true 1 1 "Timeline title")
        [void](Add-Text $s $timeline[$i][2] $x 374 220 50 14 $C.Muted $false 1 1 "Timeline detail")
    }
    [void](Add-Text $s "Resultado: cambiar el modelo en el servidor actualiza a todos sin reinstalar clientes." 156 451 648 30 18 $C.Ink3 $true 2 1 "Central takeaway")
    Add-Notes $s "Explicar por qué la arquitectura responde al requisito principal: se entrena y activa una sola versión por idioma. Los clientes no guardan copias ni ejecutan inferencia local.`n`n[Sources]`n- README.md: centralización de modelos.`n- TFG.txt: entrenamiento, activación y versión central.`n[/Sources]"

    # 8. Tecnología y seguridad
    $s = New-Slide $presentation
    Add-Header $s "Implementación" "La tecnología prioriza claridad y control" 8
    [void](Add-Text $s "DECISIONES" 68 132 320 18 11 $C.TealDark $true 1 1 "Tech label")
    [void](Add-Text $s "Python" 68 170 180 26 21 $C.Ink $true 1 1 "Python")
    [void](Add-Text $s "Núcleo, API, pruebas y automatización." 250 172 190 42 14 $C.Muted $false 1 1 "Python reason")
    [void](Add-Line $s 68 224 440 224 $C.Line 1 $false "Tech line")
    [void](Add-Text $s "Streamlit" 68 246 180 26 21 $C.Ink $true 1 1 "Streamlit tech")
    [void](Add-Text $s "Cliente web rápido y adaptable." 250 248 190 42 14 $C.Muted $false 1 1 "Streamlit reason")
    [void](Add-Line $s 68 300 440 300 $C.Line 1 $false "Tech line")
    [void](Add-Text $s "scikit-learn" 68 322 180 26 21 $C.Ink $true 1 1 "Sklearn")
    [void](Add-Text $s "Pipeline reproducible TF-IDF + MLP." 250 324 190 42 14 $C.Muted $false 1 1 "Sklearn reason")
    [void](Add-Line $s 68 376 440 376 $C.Line 1 $false "Tech line")
    [void](Add-Text $s "Gmail + Telegram" 68 398 180 42 19 $C.Ink $true 1 1 "Integrations")
    [void](Add-Text $s "Entrada OAuth y alertas opcionales." 250 400 190 42 14 $C.Muted $false 1 1 "Integrations reason")
    [void](Add-Rect $s 516 132 372 322 $C.Ink -1 0 "Security field")
    [void](Add-Text $s "CONTROLES DEL PROTOTIPO" 544 160 310 18 11 $C.TealLight $true 1 1 "Security label")
    [void](Add-Text $s "• Backend en loopback por defecto`n• Límites de petición y rutas seguras`n• Orígenes CORS restringidos`n• Credenciales fuera de Git`n• Escrituras y activación atómicas`n• Sin ejecución de adjuntos" 544 202 300 176 16 $C.White $false 1 1 "Security list")
    [void](Add-Text $s "Un despliegue público requeriría TLS, autenticación y aislamiento multiusuario." 544 390 292 45 13 (Get-Color "C9D7E0") $true 1 1 "Security caveat")
    Add-Notes $s "Relacionar cada tecnología con una decisión, no enumerar herramientas. Aclarar que SPF, DKIM y DMARC se interpretan desde las cabeceras recibidas: no hay consultas DNS ni validación criptográfica. Diferenciar los controles ya implementados de los controles necesarios para producción.`n`n[Sources]`n- TFG.txt: herramientas, seguridad y privacidad.`n- README.md: Configuración y Alcance.`n[/Sources]"

    # 9. Evaluación
    $s = New-Slide $presentation
    Add-Header $s "Evaluación" "La evaluación separa ajuste y comprobación" 9
    [void](Add-Line $s 98 270 862 270 $C.Ink 1.5 $false "Evaluation timeline")
    $evalX = @(128, 420, 712)
    foreach ($x in $evalX) { [void](Add-Circle $s ($x - 8) 262 16 $C.Blue "Evaluation dot") }
    $eval = @(
        @("1.148 + 209", "Corpus español", "Entrenamiento limpio y split oficial de prueba sin solapamientos."),
        @("65.661 + 16.416", "Corpus inglés", "División 80/20 estratificada tras deduplicar el CSV agregado."),
        @("40 + 16 EML", "Sistema completo", "Calibración separada y comprobación bilingüe con MIME y cabeceras.")
    )
    for ($i = 0; $i -lt 3; $i++) {
        $x = $evalX[$i] - 42
        [void](Add-Text $s $eval[$i][0] $x 184 230 30 23 $C.Ink $true 1 1 "Evaluation metric")
        [void](Add-Text $s $eval[$i][1] $x 312 240 28 17 $C.Ink $true 1 1 "Evaluation title")
        [void](Add-Text $s $eval[$i][2] $x 351 220 72 14 $C.Muted $false 1 1 "Evaluation detail")
    }
    [void](Add-Text $s "Principio metodológico: ninguna muestra se presenta como estimación de producción." 132 455 696 28 17 $C.Red $true 2 1 "Evaluation caveat")
    Add-Notes $s "El protocolo verifica SHA-256, elimina duplicados y contradicciones y separa la prueba antes del ajuste. Español conserva 209 casos oficiales; inglés usa una división 80/20 con semilla 42. Los seis corpus componentes no se suman al CSV agregado. Los 40 casos de calibración y 16 EML cumplen funciones distintas. DIFrauD y Zenodo son diagnósticos externos con límites explícitos.`n`n[Sources]`n- TRAINING_EVALUATION_REPORT.md.`n- evaluation/training_sources.json.`n- EVALUATION_REPORT.md.`n- EXTERNAL_EVALUATION_REPORT.md.`n[/Sources]"

    # 10. Resultados
    $s = New-Slide $presentation
    Add-Header $s "Resultados" "El modo combinado evita falsos negativos" 10
    [void](Add-Text $s "Evaluación final · 16 EML reservados" 68 113 410 20 12 $C.Soft $true 1 1 "Chart subtitle")
    # Eje y leyenda
    [void](Add-Line $s 202 458 582 458 $C.Line 1.2 $false "Chart axis")
    foreach ($tick in @(0, 25, 50, 75, 100)) {
        $x = 202 + (3.8 * $tick)
        [void](Add-Line $s $x 176 $x 458 $C.Line 0.7 $false "Grid $tick")
        [void](Add-Text $s ([string]$tick) ($x - 14) 467 28 14 9 $C.Soft $false 2 1 "Tick $tick")
    }
    $legend = @(@("Accuracy", $C.Teal), @("Recall", $C.Blue), @("F1", $C.Ink3))
    $lx = 210
    foreach ($entry in $legend) {
        [void](Add-Rect $s $lx 150 11 11 $entry[1] -1 0 "Legend swatch")
        [void](Add-Text $s $entry[0] ($lx + 17) 146 72 18 10 $C.Muted $false 1 1 "Legend")
        $lx += 100
    }
    $modes = @(
        @("Heurístico", @(100.0, 100.0, 100.0)),
        @("Neuronal", @(81.2, 87.5, 82.3)),
        @("Combinado", @(87.5, 100.0, 88.9))
    )
    $colors = @($C.Teal, $C.Blue, $C.Ink3)
    $baseY = 198
    foreach ($mode in $modes) {
        [void](Add-Text $s $mode[0] 68 ($baseY + 13) 116 22 13 $C.Ink $true 1 1 "Mode label")
        for ($j = 0; $j -lt 3; $j++) {
            $value = [double]$mode[1][$j]
            $y = $baseY + ($j * 21)
            [void](Add-Rect $s 202 $y (3.8 * $value) 13 $colors[$j] -1 0 "Result bar")
            [void](Add-Text $s (("{0:0.0}" -f $value) + " %") (208 + (3.8 * $value)) ($y - 1) 54 14 9 $C.Muted $true 1 1 "Result value")
        }
        $baseY += 94
    }
    [void](Add-Rect $s 648 154 240 112 $C.Ink -1 0 "Result callout")
    [void](Add-Text $s "100 % recall" 672 180 190 32 25 $C.White $true 1 1 "Recall result")
    [void](Add-Text $s "8/8 phishing detectados`n0 falsos negativos · 2 falsos positivos" 672 221 190 38 12 (Get-Color "C9D7E0") $false 1 1 "Recall detail")
    [void](Add-Text $s "Diagnóstico DIFrauD" 648 302 240 24 17 $C.Ink $true 1 1 "External title")
    [void](Add-Text $s "89,0 % accuracy`n93,4 % recall" 648 339 240 54 22 $C.TealDark $true 1 1 "External metrics")
    [void](Add-Text $s "Resultado complementario; no equivale a producción." 648 407 226 38 12 $C.Muted $false 1 1 "External caveat")
    Add-Notes $s "Mostrar que el combinado conserva el recall del heurístico con una accuracy alta. Explicar el único falso positivo y evitar presentar los porcentajes como rendimiento garantizado en una empresa.`n`n[Sources]`n- EVALUATION_REPORT.md: resultados globales.`n- EXTERNAL_EVALUATION_REPORT.md: resultado DIFrauD.`n[/Sources]"

    # 11. Evidencia
    $s = New-Slide $presentation
    Add-Header $s "Validación" "La evidencia cubre código, web y rendimiento" 11
    [void](Add-Line $s 480 142 480 443 $C.Line 1.2 $false "Metric vertical")
    [void](Add-Line $s 80 292 880 292 $C.Line 1.2 $false "Metric horizontal")
    $metrics = @(
        @(90, 150, "89", "pruebas Python", "Componentes, API, modelos e integraciones"),
        @(520, 150, "2", "recorridos Chromium", "Incluido navegador → Streamlit → backend"),
        @(90, 318, "96,6 %", "menos tiempo de importación", "Heurísticas tras diferir dependencias pesadas"),
        @(520, 318, "76,2 %", "menos arranque de la web", "Mejora medida; inferencia estable")
    )
    foreach ($m in $metrics) {
        [void](Add-Text $s $m[2] $m[0] $m[1] 300 52 42 $(if ($m[2] -match "%") { $C.TealDark } else { $C.Ink }) $true 1 1 "Metric value")
        [void](Add-Text $s $m[3] $m[0] ($m[1] + 58) 330 26 18 $C.Ink $true 1 1 "Metric title")
        [void](Add-Text $s $m[4] $m[0] ($m[1] + 90) 320 40 13 $C.Muted $false 1 1 "Metric detail")
    }
    Add-Notes $s "Presentar evidencia de tres niveles: pruebas de código, recorrido real del navegador y medición de rendimiento. Las advertencias de convergencia pertenecen a pruebas rápidas del MLP.`n`n[Sources]`n- README.md: Validación automática.`n- PERFORMANCE_REPORT.md.`n- docs/INTEGRATION_VALIDATION.md.`n[/Sources]"

    # 12. Demostración
    $s = New-Slide $presentation
    Add-Header $s "Demostración" "Cuatro pasos sostienen la demostración" 12
    $demo = @(
        @("01", "Arrancar", "Backend :8766 y /health"),
        @("02", "Abrir", "Streamlit conectado"),
        @("03", "Analizar", "EML BEC controlado"),
        @("04", "Explicar", "Riesgo, señales y modos")
    )
    for ($i = 0; $i -lt 3; $i++) { [void](Add-Line $s (193 + $i * 218) 247 (345 + $i * 218) 247 $C.Teal 2 $true "Demo arrow") }
    for ($i = 0; $i -lt 4; $i++) {
        $x = 72 + ($i * 218)
        [void](Add-Text $s $demo[$i][0] $x 160 176 26 13 $C.TealDark $true 2 1 "Demo number")
        [void](Add-Circle $s ($x + 67) 226 42 $(if ($i -eq 3) { $C.Teal } else { $C.Ink }) "Demo node")
        [void](Add-Text $s $demo[$i][1] $x 301 176 28 19 $C.Ink $true 2 1 "Demo title")
        [void](Add-Text $s $demo[$i][2] $x 339 176 45 14 $C.Muted $false 2 1 "Demo detail")
    }
    [void](Add-Rect $s 72 414 816 54 $C.Panel $C.Line 0 "Demo note")
    [void](Add-Text $s "Opcional: móvil en la LAN → Streamlit 0.0.0.0:8501; el backend permanece en 127.0.0.1:8766." 92 431 776 20 14 $C.Ink3 $true 2 1 "LAN note")
    Add-Notes $s "La demostración debe durar unos tres minutos. Si falla OAuth, usar los EML sintéticos y las capturas de respaldo. En el acceso móvil solo se expone Streamlit a la LAN privada.`n`n[Sources]`n- docs/DEFENSE_SCREENSHOTS.md.`n- defense_demo/README.md.`n- README.md: acceso temporal desde la red local.`n[/Sources]"

    # 13. Limitaciones
    $s = New-Slide $presentation
    Add-Header $s "Discusión" "Los límites están definidos, no ocultos" 13
    [void](Add-Text $s "LO QUE DEMUESTRA" 70 138 360 18 11 $C.TealDark $true 1 1 "Demonstrates label")
    [void](Add-Text $s "• Arquitectura cliente-servidor funcional`n• Análisis explicable y bilingüe`n• Modelos centrales compartidos`n• Evaluación reproducible y errores trazables" 70 178 366 160 17 $C.Ink $false 1 1 "Demonstrates")
    [void](Add-Line $s 480 135 480 408 $C.Line 1.4 $false "Limit divider")
    [void](Add-Text $s "LO QUE NO AFIRMA" 530 138 360 18 11 $C.Red $true 1 1 "Does not label")
    [void](Add-Text $s "• Métricas garantizadas en producción`n• Reputación online en tiempo real`n• Análisis dinámico de las páginas`n• Seguridad multiusuario para Internet" 530 178 360 160 17 $C.Ink $false 1 1 "Does not")
    [void](Add-Rect $s 70 392 820 78 $C.Ink -1 0 "Future band")
    [void](Add-Text $s "PRIORIDAD FUTURA" 94 414 150 18 11 $C.TealLight $true 1 1 "Future label")
    [void](Add-Text $s "Corpus reciente, bilingüe, anonimizado e independiente · TLS y autenticación · reputación de dominios" 264 408 596 36 15 $C.White $true 1 3 "Future items")
    Add-Notes $s "Responder con honestidad. La limitación científica principal es la falta de un corpus real reciente e independiente; no falta una función del prototipo, falta evidencia para extrapolar a producción.`n`n[Sources]`n- TFG.txt: Limitaciones y trabajo futuro.`n- CLEANUP_PLAN.md: deuda técnica que no debe ocultarse.`n[/Sources]"

    # 14. Cierre
    $s = New-Slide $presentation $C.Ink
    [void](Add-Text $s "CONCLUSIÓN" 58 50 220 20 12 $C.TealLight $true 1 1 "Closing label")
    [void](Add-Text $s "Una decisión central,`nvarias interfaces" 58 130 610 126 50 $C.White $true 1 1 "Closing title")
    [void](Add-Text $s "El prototipo separa presentación y análisis, combina evidencias explicables con aprendizaje supervisado y permite actualizar los modelos una sola vez para todos los clientes." 58 292 650 76 19 (Get-Color "C9D7E0") $false 1 1 "Closing thesis")
    [void](Add-Line $s 58 408 708 408 $C.Teal 4 $false "Closing rule")
    [void](Add-Text $s "Aportación: un detector mantenible, evaluado y preparado para evolucionar sin duplicar modelos." 58 431 650 36 16 $C.White $true 1 1 "Closing contribution")
    [void](Add-Text $s "Preguntas del tribunal" 742 436 168 26 15 $C.TealLight $true 2 1 "Questions")
    Add-Notes $s "Cierre: volver a la tesis inicial. El valor no es solo detectar; es centralizar la decisión, conservar la explicación y permitir evolución controlada. Abrir el turno de preguntas.`n`n[Sources]`n- TFG.txt: conclusiones.`n- README.md: arquitectura y alcance.`n[/Sources]"

    $presentation.SaveAs($Output, 24)
    New-Item -ItemType Directory -Path $QaDir -Force | Out-Null
    for ($i = 1; $i -le $presentation.Slides.Count; $i++) {
        $png = Join-Path $QaDir ("slide-{0:D2}.png" -f $i)
        $presentation.Slides.Item($i).Export($png, "PNG", 1920, 1080)
    }
    Write-Output "Presentación creada: $Output"
    Write-Output "Diapositivas exportadas: $($presentation.Slides.Count)"
}
finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if ($null -ne $powerPoint) { $powerPoint.Quit() }
    if ($null -ne $presentation) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    if ($null -ne $powerPoint) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
