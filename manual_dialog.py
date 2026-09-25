from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from resources import resource_path


MANUAL_HTML = """
<html>
<head>
    <style>
        body { color: #e2e8f0; background: #0f172a; font-family: sans-serif; }
        h1 { color: #38bdf8; }
        h2 { color: #7dd3fc; margin-top: 24px; }
        p, li { line-height: 1.5; }
        .hinweis { color: #a7f3d0; }
    </style>
</head>
<body>
    <h1>Benutzerhandbuch</h1>
    <p>Mit dem Spielplan Generator richten Sie Jungscharen, Gruppen,
    Spiele und Runden ein und erstellen daraus einen Spielplan als
    Excel-Datei.</p>
    <p class="hinweis"><b>Wichtig für die Begegnungen:</b> Teams aus
    derselben Jungschar spielen nicht gegeneinander. Wenn jedes Team
    grundsätzlich gegen jedes andere Team spielen können soll, legen
    Sie jedes Team als eigene Jungschar mit genau einem Team an.</p>

    <h2>Schritt 1: Jungscharen einrichten</h2>
    <ol>
        <li>Wählen Sie links <b>Gruppen</b>.</li>
        <li>Legen Sie bei <b>Anzahl Jungscharen</b> fest, wie viele
        Jungscharen teilnehmen. Für einen Spielplan sind mindestens
        zwei Jungscharen erforderlich.</li>
        <li>Ändern Sie den Namen einer Jungschar im Eingabefeld neben
        <b>Jungschar 1 – Name</b> (die Nummer passt sich je Eintrag an)
        und legen Sie daneben die Anzahl der Teams fest.</li>
        <li>Ändern Sie die einzelnen Teamnamen im Abschnitt
        <b>Teamnamen (hier ändern)</b> unterhalb der Jungscharen.</li>
    </ol>

    <h2>Schritt 2: Spiele benennen</h2>
    <ol>
        <li>Öffnen Sie links die Seite <b>Spiele</b>.</li>
        <li>Legen Sie die Anzahl der Spiele fest.</li>
        <li>Geben Sie jedem Spiel einen eindeutigen, gut erkennbaren Namen.</li>
    </ol>

    <h2>Schritt 3: Runden festlegen</h2>
    <ol>
        <li>Öffnen Sie links die Seite <b>Runden</b>.</li>
        <li>Stellen Sie ein, wie viele Runden gespielt werden sollen.</li>
        <li>Stellen Sie bei <b>Suchzeit (Sekunden)</b> ein, wie lange
        nach einem möglichst ausgewogenen Spielplan gesucht werden soll.
        Der Standardwert beträgt 60 Sekunden.</li>
    </ol>

    <h2>Schritt 4: Angaben prüfen und Spielplan erstellen</h2>
    <ol>
        <li>Kontrollieren Sie, ob alle Jungscharen, Gruppen und Spiele einen Namen haben.</li>
        <li>Klicken Sie auf <b>Spielplan generieren</b>.</li>
        <li>Während der Berechnung sehen Sie den Fortschritt. Mit
        <b>Generierung abbrechen</b> können Sie den Vorgang stoppen.</li>
    </ol>

    <h2>Schritt 5: Excel-Datei speichern</h2>
    <p>Nach erfolgreicher Berechnung wählen Sie im Speichern-Dialog
    einen Speicherort und Dateinamen. Bestätigen Sie anschließend das Speichern.</p>

    <h2>Ergebnis und weitere Funktionen</h2>
    <p>Die Excel-Datei enthält den Spielplan sowie Übersichten zu
    Spielhäufigkeiten, Begegnungen und zur Teilnahme der Gruppen:
    <b>Schedule</b>, <b>Game Counts</b>, <b>Team Matchups</b>,
    <b>Game Team Counts</b> und <b>Team Game Totals</b>.</p>
    <p class="hinweis">Mit <b>Eingaben zurücksetzen</b> können Sie
    alle Einstellungen auf die Standardwerte zurücksetzen. Dabei
    werden Ihre aktuellen Eingaben verworfen.</p>
</body>
</html>
"""


class ManualDialog(QDialog):
    """Separate window containing the German step-by-step user guide."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spielplan Generator – Benutzerhandbuch")
        self.setWindowIcon(QIcon(str(resource_path("app_icon.ico"))))
        self.resize(760, 700)

        layout = QVBoxLayout(self)
        manual = QTextBrowser(self)
        manual.setOpenExternalLinks(False)
        manual.setHtml(MANUAL_HTML)
        layout.addWidget(manual)

        close_button = QPushButton("Schließen", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
