#ifndef APP_MAINWINDOW_HPP
#define APP_MAINWINDOW_HPP

#include <QMainWindow>

#include "beaconeditor.hpp"
#include "model.hpp"
#include "pathcontroller.hpp"
#include "scene.hpp"

QT_BEGIN_NAMESPACE

namespace Ui {
    class MainWindow;
}

QT_END_NAMESPACE

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(Model *model, QWidget *parent = nullptr);

    ~MainWindow() override;

private:
    Ui::MainWindow *m_ui;

    Model *m_model;

    BeaconEditor *m_beaconEditor;
    PathController *m_pathController;
    Scene *m_scene;

public slots:
    void openPathFile();

    void savePathFile();
};

#endif  //APP_MAINWINDOW_HPP
