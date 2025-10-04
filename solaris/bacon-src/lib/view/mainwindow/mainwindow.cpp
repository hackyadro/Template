#include "mainwindow.hpp"

#include <QFileDialog>

#include "ui_mainwindow.h"

#include <QObject>

#include "model_utils.hpp"

MainWindow::MainWindow(Model* model, QWidget* parent)
    : QMainWindow(parent),
      m_ui(new Ui::MainWindow),
      m_model(model),
      m_beaconEditor(new BeaconEditor(model)),
      m_pathController(new PathController(model)),
      m_scene(new Scene(m_model)) {
    m_ui->setupUi(this);

    setWindowTitle("Bacon");

    m_ui->tabWidget->removeTab(0);
    m_ui->tabWidget->removeTab(0);
    m_ui->tabWidget->addTab(m_pathController, "Controller");
    m_ui->tabWidget->addTab(m_beaconEditor, "Beacon Editor");
    m_ui->verticalLayout->addWidget(m_scene);

    connect(m_beaconEditor, &BeaconEditor::accepted, m_model,
            &Model::beaconChanged);
    connect(m_model, &Model::signalBeaconsChanged, m_beaconEditor,
            &BeaconEditor::updateBeacons);
    connect(m_model, &Model::signalBeaconsChanged, m_scene,
            &Scene::beaconChanged);
    connect(m_pathController, &PathController::urlChanged, m_model,
            &Model::onUrlChanged);

    connect(m_model, &Model::dataChanged, m_scene, &Scene::espChanged);
    connect(m_model, &Model::pointAddedSignal, m_pathController,
            &PathController::addPathPoint);

    setWindowIcon(QIcon(":/assets/assets/icon.png"));
    m_ui->actionOpen_beacon->setIcon(QIcon(":/assets/assets/open.png"));
    m_ui->actionSave_beacon->setIcon(QIcon(":/assets/assets/save.png"));
    m_ui->actionSave_Path->setIcon(QIcon(":/assets/assets/save.png"));
    m_ui->actionOpen_path->setIcon(QIcon(":/assets/assets/open.png"));

    connect(m_ui->actionOpen_beacon, &QAction::triggered, m_beaconEditor,
            &BeaconEditor::openFile);
    connect(m_ui->actionSave_beacon, &QAction::triggered, m_beaconEditor,
            &BeaconEditor::saveIntoFile);

    connect(m_ui->actionOpen_path, &QAction::triggered, this,
            &MainWindow::openPathFile);

    connect(m_ui->actionSave_Path, &QAction::triggered, this,
            &MainWindow::savePathFile);

    connect(m_model, &Model::pathChanged, m_pathController,
            &PathController::setPath);

    connect(m_model, &Model::pathChanged, m_scene,
            &Scene::onPathChanged);

    connect(m_model, &Model::satPath, m_scene,
            &Scene::onPathSeted);

    connect(m_pathController, &PathController::pathReseted, m_model,
            &Model::onResetPath);

    m_beaconEditor->acceptedSlot();
}

MainWindow::~MainWindow() {
    delete m_ui;
    delete m_beaconEditor;
    delete m_scene;
}

void MainWindow::openPathFile() {
    QString filePath = QFileDialog::getOpenFileName(
        nullptr,
        QObject::tr("Open File"),  // Заголовок окна
        QDir::currentPath(),       // Начальная директория
        QObject::tr("All Files (*);;Text Files (*.txt)")  // Фильтры
    );
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return;
    }
    QTextStream in(&file);
    in.setEncoding(QStringConverter::Utf8);
    const QString fileContent = in.readAll();
    m_model->setPath(model_utils::parseContent(fileContent.toStdString()));
}

void MainWindow::savePathFile() {
    QString filePath =
        QFileDialog::getSaveFileName(nullptr, QObject::tr("Save Text File"), "",
                                     "Text Files (*.txt);;All Files (*)");
    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return;
    }
    QTextStream out(&file);
    out.setEncoding(QStringConverter::Utf8);
    const auto path = m_model->path();
    const auto content = model_utils::fetchContent(path);
    out << content;
    file.close();
}
