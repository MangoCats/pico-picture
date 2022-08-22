// PicturePoster Copyright (c) 2022 MangoCats - All Rights Reserved
// See: LICENSE file in project root for details.
#include "mainwindow.h"

#include <QApplication>
#include <QLocale>
#include <QTranslator>
#include <QSettings>

int main(int argc, char *argv[])
{   QCoreApplication::setOrganizationName("MangoCats");
    QCoreApplication::setOrganizationDomain("mangocats.com");
    QCoreApplication::setApplicationName("PicturePoster");
    QSettings::setDefaultFormat( QSettings::IniFormat );

    QApplication a(argc, argv);

    QTranslator translator;
    const QStringList uiLanguages = QLocale::system().uiLanguages();
    for (const QString &locale : uiLanguages) {
        const QString baseName = "PicturePoster_" + QLocale(locale).name();
        if (translator.load(":/i18n/" + baseName)) {
            a.installTranslator(&translator);
            break;
        }
    }
    MainWindow w;
    w.show();
    return a.exec();
}
