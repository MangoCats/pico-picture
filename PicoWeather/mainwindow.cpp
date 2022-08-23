// PicoWeather Copyright (c) 2022 MangoCats - All Rights Reserved
// See: LICENSE file in project root for details.
#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QHttpMultiPart>
#include <QSettings>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonValue>
#include <QPainter>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    readSettings();
    mgr = new QNetworkAccessManager(this);
    connect(mgr, &QNetworkAccessManager::finished,
            this, &MainWindow::replyFinished );

    connect(&autoUpdate,SIGNAL(timeout()),SLOT(on_update_clicked()));
    autoUpdate.setSingleShot( false );
    autoUpdate.start( ui->interval->value() * 60000 );
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
  ui->interval->setValue ( settings.value( "interval", 5  ).toInt()    );
  ui->username->setText  ( settings.value( "username", "" ).toString() );
  ui->password->setText  ( settings.value( "password", "" ).toString() );
  ui->privacy->setChecked( settings.value( "privacy", false ).toBool() );
}

void MainWindow::writeSettings()
{ QSettings settings;
  settings.setValue( "address" , ui->address ->text()  );
  settings.setValue( "lat"     , ui->lat     ->text()  );
  settings.setValue( "lon"     , ui->lon     ->text()  );
  settings.setValue( "interval", ui->interval->value() );
  settings.setValue( "username", ui->username->text()  );
  settings.setValue( "password", ui->password->text()  );
  settings.setValue( "privacy" , ui->privacy->isChecked() );
  settings.setValue( "geometry", saveGeometry() );
  settings.setValue( "state"   , saveState()    );
}

void MainWindow::on_privacy_toggled( bool priv )
{ ui->privateFrame->setHidden( priv ); }

void MainWindow::on_interval_valueChanged( int i )
{ autoUpdate.setInterval( i * 60000 ); }

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
    QUrl url = QUrl( "https://api.meteomatics.com/now-1H--now+12H:PT5M/t_2m:F,precip_1h:mm/" + ui->lat->text() + "," + ui->lon->text() + "/json" );
    QNetworkRequest request(url);
    request.setRawHeader("Authorization", "Basic " + b64 );
    mgr->get( request );
}

/**
 * @brief MainWindow::replyFinished - both json weather forecasts and image PUT replies
 * @param rep - pointer to the reply
 */
void MainWindow::replyFinished(QNetworkReply *rep)
{ QByteArray ba = rep->readAll();
  ui->result->setText( "Reply:'" + readReply(ba) + "'" );
  rep->deleteLater();
}

/**
 * @brief MainWindow::readReply - determine if the reply is json or not
 *   if it is, do further analysis of the weather information and return the result code
 *   if it is not, just return the data as a string.
 * @param ba - reply data
 * @return - string to be displayed, result code for json and whole array for non-json
 */
QString MainWindow::readReply( const QByteArray &ba )
{ QJsonDocument jd = QJsonDocument::fromJson( ba );
  if ( !jd.isObject() )
    return QString::fromUtf8( ba );
  QString status = "unknown";
  QJsonObject jo = jd.object();
  if ( jo.contains( "status") )
    status = jo.value( "status" ).toString();
  if ( !jo.contains( "data" ) )
    status.append( " no data." );
   else
    { QJsonValue jvData = jo.value( "data" );
      if ( !jvData.isArray() )
        status.append( " data is not an array." );
       else
        { temps.clear();
          rains.clear();
          QJsonArray jaData = jvData.toArray();
          foreach ( QJsonValue jvParam, jaData )
            { if ( jvParam.isObject() )
                { QJsonObject joParam = jvParam.toObject();
                  if ( joParam.contains( "parameter" ) )
                    { QString pv = joParam.value( "parameter" ).toString();
                      if ( pv == "t_2m:F" ) // Temperature values
                        { if ( joParam.contains( "coordinates" ) )
                            { QJsonValue jvCoord = joParam.value( "coordinates" );
                              if ( jvCoord.isArray() )
                                { QJsonArray jaCoord = jvCoord.toArray();
                                  if ( jaCoord.size() >= 1 )
                                    { QJsonValue jvC1 = jaCoord.at(0);
                                      if ( jvC1.isObject() )
                                        { QJsonObject joC1 = jvC1.toObject();
                                          if ( joC1.contains( "dates" ) )
                                            { QJsonValue jvDates = joC1.value( "dates" );
                                              if ( jvDates.isArray() )
                                                { QJsonArray jaDates = jvDates.toArray();
                                                  foreach ( QJsonValue date, jaDates )
                                                    { if ( date.isObject() )
                                                        { QJsonObject joDate = date.toObject();
                                                          if ( joDate.contains( "value" ) )
                                                            { QJsonValue jvValue = joDate.value( "value" );
                                                              if ( jvValue.isDouble() )
                                                                temps.append( jvValue.toDouble() );
                                                            } // date contains value
                                                        } // date is Object
                                                    } // iterate dates
                                                } // dates is array
                                            } // coordinate[0] contains dates
                                        } // coordinate[0] is Object
                                    } // coordinates size >= 1
                                } // coordinates is array
                            } // contains coordinates
                        } // Temperature values
                       else if ( pv == "precip_1h:mm" ) // Rainfall accumulations
                        { if ( joParam.contains( "coordinates" ) )
                            { QJsonValue jvCoord = joParam.value( "coordinates" );
                              if ( jvCoord.isArray() )
                                { QJsonArray jaCoord = jvCoord.toArray();
                                  if ( jaCoord.size() >= 1 )
                                    { QJsonValue jvC1 = jaCoord.at(0);
                                      if ( jvC1.isObject() )
                                        { QJsonObject joC1 = jvC1.toObject();
                                          if ( joC1.contains( "dates" ) )
                                            { QJsonValue jvDates = joC1.value( "dates" );
                                              if ( jvDates.isArray() )
                                                { QJsonArray jaDates = jvDates.toArray();
                                                  foreach ( QJsonValue date, jaDates )
                                                    { if ( date.isObject() )
                                                        { QJsonObject joDate = date.toObject();
                                                          if ( joDate.contains( "value" ) )
                                                            { QJsonValue jvValue = joDate.value( "value" );
                                                              if ( jvValue.isDouble() )
                                                                rains.append( jvValue.toDouble() );
                                                            } // date contains value
                                                        } // date is Object
                                                    } // iterate dates
                                                } // dates is array
                                            } // coordinate[0] contains dates
                                        } // coordinate[0] is Object
                                    } // coordinates size >= 1
                                } // coordinates is array
                            } // contains coordinates
                        } // Rainfall accumulations
                    } // object contains parameter
                } // is object
            } // each parameter array item
          if ( temps.size() > 0 )
            renderWeather();
           else
            status.append( " no temp data" );
        } // data is not an array
    } // no data
  return status;
}

/**
 * @brief MainWindow::renderWeather - temps and or rains have updated
 *   draw the new weather image and send it to the display
 */
void MainWindow::renderWeather()
{ float minTemp =  100.0;
  float maxTemp = -100.0;
  float maxRain =    0.0;
  int n = 0;
  int nowI = 13;
  foreach ( float t, temps )
    { if ( t < minTemp ) minTemp = t;
      if ( t > maxTemp ) maxTemp = t;
      n++;
    }
  if ( n < 1 )
    return;
  if ( nowI >= n )
    nowI = n-1;

  foreach ( float mm, rains )
    if ( mm > maxRain )
      maxRain = mm;

  // Set ranges
  if ( maxRain < 12.7 )
    maxRain = 12.7;
  float midTemp = (minTemp + maxTemp) * 0.5;
  float tempRng = maxTemp - minTemp;
  if ( tempRng < 10.0 )
    tempRng = 10.0;
  QString minTempS = QString::number( minTemp );
  QString maxTempS = QString::number( maxTemp );
  minTemp = midTemp - tempRng * 0.5;
  // maxTemp = midTemp + tempRng * 0.5;

  int w = SCREEN_WIDTH  * 4;
  int h = SCREEN_HEIGHT * 4;
  QImage im = QImage(w,h,QImage::Format_RGB32);
  im.fill(Qt::black);

  float tRain;
  int i = 0;
  int x0 = 0;

  QPainter p;
  if (p.begin(&im))
    { int lTempY = (int)(((float)h)*(temps.at(0) - minTemp)/tempRng);
      // The now line
      int xn = (nowI * w) / n;
      p.setPen(QPen(QColor(64, 64, 64), 4, Qt::SolidLine, Qt::SquareCap, Qt::BevelJoin));
      p.drawLine( xn, h-1, xn, 0 );

      // Temperature numerics
      p.setPen(QPen(QColor(0, 200, 0)));
      p.setFont(QFont("Arial", 160, QFont::Bold));
      p.drawText(im.rect(), Qt::AlignTop    | Qt::AlignLeft , QString::number(temps.at(nowI)) );
      p.setFont(QFont("Arial",  80, QFont::Bold));
      p.drawText(im.rect(), Qt::AlignTop    | Qt::AlignRight, maxTempS );
      p.drawText(im.rect(), Qt::AlignBottom | Qt::AlignRight, minTempS );

      foreach ( float tTemp, temps )
        { if ( i < rains.size() )
            tRain = rains.at( i );
           else
            tRain = 0.0;
          int yRain = (int)(((float)(h-20) * tRain) / maxRain);
          i++;
          int x1 = (i * w) / n;

          // Rain bars
          if ( tRain > 0.0 )
            { p.setPen(QPen(QColor(0, 192, 255, 0xC0), 1, Qt::SolidLine, Qt::SquareCap, Qt::BevelJoin));
              for ( int xi = x0; xi < x1; xi++ )
                p.drawLine( xi, h-1, xi, h-20-yRain );
            }

          // Temp line
          int tempY = (int)(((float)h)*(tTemp - minTemp)/tempRng);
          p.setPen(QPen(QColor(255, 127, 0), 6, Qt::SolidLine, Qt::SquareCap, Qt::BevelJoin));
          p.drawLine( x0, lTempY, x1, tempY );
          lTempY = tempY;
          x0 = x1;
        }
      p.end();
    }

  pm.convertFromImage( im.scaled(SCREEN_WIDTH,SCREEN_HEIGHT,Qt::IgnoreAspectRatio,Qt::SmoothTransformation ) );
  ui->preview->setPixmap( pm );
  on_send_clicked();
}
