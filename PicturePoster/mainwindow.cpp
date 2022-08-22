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
}

void MainWindow::on_send_clicked()
{ QByteArray ba = imageData();
  ui->result->setText( QString( "Sending %1 bytes" ).arg( ba.size() ) );
  postRequest( ba );
}

QByteArray MainWindow::imageData()
{ QByteArray ba;
  // TODO: translate pm to ba
  return ba;
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
