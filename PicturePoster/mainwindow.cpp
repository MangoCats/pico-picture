#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QHttpMultiPart>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    mgr = new QNetworkAccessManager(this);
    connect(mgr, &QNetworkAccessManager::finished,
            this, &MainWindow::replyFinished );

}

MainWindow::~MainWindow()
{
    delete ui;
    delete mgr;
}

void MainWindow::on_browse_clicked()
{ QFileDialog fd;
  QString filename = fd.getOpenFileName( this, tr( "Choose Image File" ), "", tr("Image Files (*.png *.jpg *.bmp)") );
  QFile file( filename );
  if ( !file.open( QIODevice::ReadOnly ) )
    { ui->preview->setText( QString( tr( "Could not open %1 for reading." ) ).arg( filename ) );
      return;
    }
  file.close();
  if ( !pm.load( filename ) )
    { ui->preview->setText( QString( tr( "Could not load %1 as an image." ) ).arg( filename ) );
      return;
    }
  ui->preview->setPixmap( pm.scaled(SCREEN_WIDTH,SCREEN_HEIGHT,Qt::KeepAspectRatio) );
  ui->filename->setText( filename );
}

void MainWindow::on_send_clicked()
{ QByteArray ba = imageData();
  ui->result->setText( QString( "Sending %1 bytes" ).arg( ba.size() ) );
  postRequest( ba );
}

QByteArray MainWindow::imageData()
{ QByteArray ba;
  if ( pm.isNull() )
    return ba;
  QPixmap pms = pm.scaled(SCREEN_WIDTH,SCREEN_HEIGHT,Qt::KeepAspectRatio);
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

QByteArray MainWindow::pixTrans( const QRgb &px )
{ QByteArray b2; // Converting to 565 specifically for the Waveshare screen
  quint16 r = qRed( px ) >> 3;
  quint16 g = qGreen( px ) >> 2;
  quint16 b = qBlue( px ) >> 3;
  quint16 p = g | (r << 6) | (b << 11);
  b2.append( p & 0xFF );
  b2.append( p >> 8 );
  return b2;
}

void MainWindow::postRequest( const QByteArray &postData )
{
    QUrl url = QUrl( "http://" + ui->address->text() );

    QHttpMultiPart *http = new QHttpMultiPart();

    QHttpPart receiptPart;
    receiptPart.setHeader(QNetworkRequest::ContentTypeHeader  , "application/octet-stream" );
    receiptPart.setHeader(QNetworkRequest::ContentLengthHeader, postData.size() );
    receiptPart.setBody(postData);

    http->append(receiptPart);

    mgr->post( QNetworkRequest(url), http );

    // http->deleteLater();
}

void MainWindow::replyFinished(QNetworkReply *rep)
{ ui->result->setText( "Reply:'" + QString::fromUtf8( rep->readAll() ) + "'" );
  rep->deleteLater();
}
