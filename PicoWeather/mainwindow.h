#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QNetworkReply>
#include <QNetworkAccessManager>

#define SCREEN_WIDTH  240
#define SCREEN_HEIGHT 135

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
            MainWindow(QWidget *parent = nullptr);
           ~MainWindow();
      void  closeEvent(QCloseEvent *event);
      void  readSettings();
      void  writeSettings();
      void  putRequest(const QByteArray &);
QByteArray  imageData();
QByteArray  pixTrans( const QRgb & );

public slots:
      void  on_send_clicked();
      void  on_privacy_toggled( bool );
      void  replyFinished(QNetworkReply *);

private:
       Ui::MainWindow *ui;
              QPixmap  pm;
QNetworkAccessManager *mgr;

};
#endif // MAINWINDOW_H