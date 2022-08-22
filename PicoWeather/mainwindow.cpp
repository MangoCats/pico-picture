// PicoWeather Copyright (c) 2022 MangoCats - All Rights Reserved
// See: LICENSE file in project root for details.
#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QHttpMultiPart>
#include <QSettings>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    readSettings();
    mgr = new QNetworkAccessManager(this);
    connect(mgr, &QNetworkAccessManager::finished,
            this, &MainWindow::replyFinished );
}

MainWindow::~MainWindow()
{
    delete ui;
    delete mgr;
}

void MainWindow::closeEvent(QCloseEvent *event)
{ writeSettings();
  // int i = 100;
  // while (( --i > 0 ) && !readyToShutdown() )
  //   { QThread::usleep(5000);
  //     QApplication::processEvents( QEventLoop::AllEvents,5 );
  //   }
  QMainWindow::closeEvent(event);
}

void MainWindow::readSettings()
{ QSettings settings;
          restoreGeometry( settings.value( "geometry" ).toByteArray()  );
          restoreState   ( settings.value( "state"    ).toByteArray()  );
  ui->address ->setText  ( settings.value( "address" , "" ).toString() );
  ui->lat     ->setText  ( settings.value( "lat"     , "" ).toString() );
  ui->lon     ->setText  ( settings.value( "lon"     , "" ).toString() );
  ui->username->setText  ( settings.value( "username", "" ).toString() );
  ui->password->setText  ( settings.value( "password", "" ).toString() );
  ui->privacy->setChecked( settings.value( "privacy", false ).toBool() );
}

void MainWindow::writeSettings()
{ QSettings settings;
  settings.setValue( "address" , ui->address ->text() );
  settings.setValue( "lat"     , ui->lat     ->text() );
  settings.setValue( "lon"     , ui->lon     ->text() );
  settings.setValue( "username", ui->username->text() );
  settings.setValue( "password", ui->password->text() );
  settings.setValue( "privacy" , ui->privacy->isChecked() );
  settings.setValue( "geometry", saveGeometry() );
  settings.setValue( "state"   , saveState()    );
}

void MainWindow::on_privacy_toggled( bool priv )
{ ui->privateFrame->setHidden( priv ); }

/**
 * @brief MainWindow::on_send_clicked - translates whatever is in pm
 *   for sending to the Pi Pico W
 */
void MainWindow::on_send_clicked()
{ QByteArray ba = imageData();
  if ( ba.size() > 1000 )
    { ui->result->setText( QString( "Sending %1 bytes" ).arg( ba.size() ) );
      putRequest( ba );
    }
   else
    { ui->result->setText( QString( "Image data too small: %1 bytes, not sending." ).arg( ba.size() ) );
    }
}

/**
 * @brief MainWindow::imageData
 * @return the image on the screen, translated for the Waveshare display
 */
QByteArray MainWindow::imageData()
{ QByteArray ba;
  if ( pm.isNull() )
    return ba;
  QPixmap pms = pm.scaled(SCREEN_WIDTH,SCREEN_HEIGHT,Qt::IgnoreAspectRatio);
  if ( pms.isNull() )
    return ba;
  QImage im = pms.toImage();
  if ( im.isNull() )
    return ba;
  for ( int j = 0; j < SCREEN_HEIGHT; j++ )
    for ( int i = 0; i < SCREEN_WIDTH; i++ )
      ba.append( pixTrans(im.pixel(i,j) ) );
  return ba;
}

/**
 * @brief MainWindow::pixTrans - translate the color of a single pixel
 * @param px - standard RGB color
 * @return 2 bytes carrying 565 format RGB tailored for easy ingestion into the Waveshare framebuffer
 */
QByteArray MainWindow::pixTrans( const QRgb &px )
{ QByteArray b2;
  quint16 r = qRed( px ) >> 3;
  quint16 g = qGreen( px ) >> 2;
  quint16 b = qBlue( px ) >> 3;
  quint16 p = b | (g << 5) | (r << 11);
  b2.append( p & 0xFF );
  b2.append( p >> 8 );
  return b2;
}

/**
 * @brief MainWindow::putRequest - goes to the Pi Pico W
 * @param putData - image data to send to the screen
 */
void MainWindow::putRequest( const QByteArray &putData )
{
    QUrl url = QUrl( "http://" + ui->address->text() );
    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader  , "application/octet-stream" );
    request.setHeader(QNetworkRequest::ContentLengthHeader, putData.size()             );
    mgr->put( request, putData );
}

/**
 * @brief MainWindow::on_update_clicked - get a new weather update
 * https://api.meteomatics.com/2022-08-22T00:00:00Z/t_2m:C/52.520551,13.461804/html
 */
void MainWindow::on_update_clicked()
{   QString as = ui->username->text()+":"+ui->password->text();
    QByteArray ba = as.toUtf8();
    QByteArray b64 = ba.toBase64();
    QUrl url = QUrl( "https://api.meteomatics.com/now-1H--now+6H:PT10M/t_2m:F,precip_1h:mm/" + ui->lat->text() + "," + ui->lon->text() + "/json" );
    QNetworkRequest request(url);
    request.setRawHeader("Authorization", "Basic " + b64 );
    mgr->get( request );
}

/**
 * @brief MainWindow::replyFinished - both json weather forecasts and image PUT replies
 * @param rep - pointer to the reply
 */
void MainWindow::replyFinished(QNetworkReply *rep)
{ ui->result->setText( "Reply:'" + QString::fromUtf8( rep->readAll() ) + "'" );
  rep->deleteLater();
}
