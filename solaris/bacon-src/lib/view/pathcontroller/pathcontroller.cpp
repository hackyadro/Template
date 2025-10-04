#include "pathcontroller.hpp"

#include <qwidget.h>
#include <QPushButton>
#include "model.hpp"
#include "ui_pathcontroller.h"
#include "utils.hpp"

PathController::PathController(Model* model, QWidget* parent)
    : QWidget(parent),
      m_ui(new Ui::PathController),
      m_model(model),
      m_list(new QStandardItemModel(0, 3, this)) {
    m_ui->setupUi(this);
    m_list->setHeaderData(0, Qt::Horizontal, "X");
    m_list->setHeaderData(1, Qt::Horizontal, "Y");
    m_list->setHeaderData(2, Qt::Horizontal, "Time");
    m_ui->tableView->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_ui->tableView->setModel(m_list);

    m_ui->resetBtn->setIcon(QIcon(":/assets/assets/stop.png"));
    m_ui->startBtn->setIcon(QIcon(":/assets/assets/play.png"));
    m_ui->stopBtn->setIcon(QIcon(":/assets/assets/pause.png"));
    m_ui->acceptUrlBtn->setIcon(QIcon(":/assets/assets/ok.png"));
    m_ui->freqBtn->setIcon(QIcon(":/assets/assets/ok.png"));
    m_ui->freqBtn->setText("");
    m_ui->acceptUrlBtn->setText("");
    m_ui->resetBtn->setText("");
    m_ui->startBtn->setText("");
    m_ui->stopBtn->setText("");
    m_ui->resetBtn->setIconSize(QSize(32, 32));
    m_ui->startBtn->setIconSize(QSize(32, 32));
    m_ui->stopBtn->setIconSize(QSize(32, 32));
    m_ui->acceptUrlBtn->setIconSize(QSize(24, 24));
    m_ui->freqBtn->setIconSize(QSize(24, 24));
    m_ui->freqBtn->setFixedSize(QSize(24, 24));
    m_ui->acceptUrlBtn->setFixedSize(QSize(24, 24));
    m_ui->resetBtn->setToolTip("reset");
    m_ui->stopBtn->setToolTip("stop");
    m_ui->startBtn->setToolTip("start");
    m_ui->resetBtn->setFlat(true);
    m_ui->stopBtn->setFlat(true);
    m_ui->startBtn->setFlat(true);
    const QString style =
        "QPushButton {"
        "  border: none;"             // убираем рамку
        "  background: transparent;"  // убираем фон
        "}"
        "QPushButton:hover {"
        "  background: rgba(0,0,0,0.1);"  // опционально: легкий эффект при наведении
        "}";
    m_ui->resetBtn->setStyleSheet(style);
    m_ui->startBtn->setStyleSheet(style);
    m_ui->stopBtn->setStyleSheet(style);
    m_ui->freqBtn->setStyleSheet(style);
    m_ui->acceptUrlBtn->setStyleSheet(style);

    connect(m_ui->acceptUrlBtn, &QPushButton::clicked, this,
            &PathController::onUrlAccepted);
    connect(m_ui->freqBtn, &QPushButton::clicked, this,
            &PathController::onFreqAccepted);
    connect(m_ui->resetBtn, &QPushButton::clicked, this,
            &PathController::resetPath);

    connect(m_ui->startBtn, &QPushButton::clicked, m_model, &Model::onStarted);
    connect(m_ui->stopBtn, &QPushButton::clicked, m_model, &Model::onStopped);
}

PathController::~PathController() {
    delete m_ui;
}

void PathController::setPath() {
    const auto path = m_model->path();
    const auto size = path.size();
    m_list->setRowCount(size);
    for (int row = 0; row < path.size(); ++row) {
        const QPointF &p = path[row];
        m_list->setItem(size - row - 1, 0, new QStandardItem(QString::number(p.x())));
        m_list->setItem(size - row - 1, 1, new QStandardItem(QString::number(p.y())));
    }

    m_ui->tableView->horizontalHeader()->setSectionResizeMode(
        QHeaderView::Stretch);
    m_ui->tableView->verticalHeader()->setSectionResizeMode(
        QHeaderView::ResizeToContents);
    m_ui->tableView->setSelectionBehavior(QAbstractItemView::SelectRows);
}

void PathController::resetPath() {
    m_list->removeRows(0, m_list->rowCount());
    emit pathReseted();
}

void PathController::addPathPoint(const QPointF& pnt) {
    m_list->insertRow(0);
    m_list->setItem(0, 0, new QStandardItem(QString::number(pnt.x())));
    m_list->setItem(0, 1, new QStandardItem(QString::number(pnt.y())));
    m_list->setItem(0, 2,
                    new QStandardItem(QString::fromStdString(currentTime())));
}

void PathController::onUrlAccepted() {
    auto url = m_ui->urlEdit->text();
    if (!isValidIPv4WithPort(url)) {
        m_ui->urlEdit->setText("127.0.0.1:1883");
        url = m_ui->urlEdit->text();
    };
    emit urlChanged(url);
}

void PathController::onFreqAccepted() {
    const float freq = m_ui->freqSpinBox->value();
    emit freqChanged(freq);
}
