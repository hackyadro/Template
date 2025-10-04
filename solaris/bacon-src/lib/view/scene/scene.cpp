#include "scene.hpp"
#include <qcolor.h>
#include <qevent.h>
#include <qpoint.h>
#include <QGraphicsView>
#include <QTimer>
#include <QVBoxLayout>
#include <cmath>

#include "beaconitem.hpp"
#include "const.hpp"
#include "espitem.hpp"
#include "griditem.hpp"
#include "pointitem.hpp"

Scene::Scene(Model* model, QWidget* parent)
    : QWidget(parent),
      m_model(model),
      m_scene(new QGraphicsScene(this)),
      m_view(new QGraphicsView(m_scene, this)) {
    // Размещение QGraphicsView во всём окне
    m_layout = new QVBoxLayout(this);
    m_layout->setContentsMargins(0, 0, 0, 0);
    m_layout->addWidget(m_view);
    setLayout(m_layout);

    m_view->setDragMode(QGraphicsView::ScrollHandDrag);
    m_view->setAutoFillBackground(true);

    m_view->setRenderHint(QPainter::Antialiasing);
    m_view->setSceneRect(-COUNT_CELLS * CELL_SIZE, -COUNT_CELLS * CELL_SIZE,
                         COUNT_CELLS * CELL_SIZE * 2,
                         COUNT_CELLS * CELL_SIZE * 2);
    m_view->setBackgroundBrush(QBrush(kBackgroundColor));

    setupBasicScene();
}

Scene::~Scene() {
    delete m_view;
    delete m_esp;
    delete m_layout;
}

void Scene::keyPressEvent(QKeyEvent* event) {
    QWidget::keyPressEvent(event);
    if (event->key() == Qt::Key_Plus) {
        if (m_zoomCounter < MAX_ZOOM) {
            m_view->scale(1.1, 1.1);
            m_zoomCounter++;
        }
    } else if (event->key() == Qt::Key_Minus) {
        if (-m_zoomCounter < MAX_ZOOM) {
            m_view->scale(0.9, 0.9);
            m_zoomCounter--;
        }
    }
}

void Scene::setupBasicScene() {
    clearScene();
    m_scene->addItem(new GridItem(CELL_SIZE));  // сетка
    m_esp = new EspItem("CONNECTED", 10);
    m_scene->addItem(m_esp);
    m_esp->setPos(0, 0);
    m_pathItems = new QGraphicsPathItem();
    m_scene->addItem(m_pathItems);
    m_pathItems->setPen(QPen(kPathColor[0], 2));
}

void Scene::clearScene() {
    m_scene->clear();
}

void Scene::beaconChanged() {
    setupBasicScene();
    const auto beacons = m_model->beacons();
    for (const auto& beacon : beacons) {
        const auto pos = beacon.pos();
        m_scene->addItem(new BeaconItem(beacon.name(), pos.x(), pos.y()));
    }
    update();
}

void Scene::espChanged() {
    const auto eo = m_model->esp();
    const auto pos = eo.pos();
    m_esp->setPos(pos.x() * CELL_SIZE, -pos.y() * CELL_SIZE);
    m_esp->setStatus(m_model->status());
    const auto path = m_model->path();
    QPainterPath pp;
    if (path.isEmpty()) {
        pp.moveTo(QPointF(pos.x() * CELL_SIZE, -pos.y() * CELL_SIZE));
    } else {
        pp.moveTo(QPointF(path[0].x() * CELL_SIZE, -path[0].y() * CELL_SIZE));
        for (int i = 1; i < path.size(); i++) {
            pp.lineTo(
                QPointF(path[i].x() * CELL_SIZE, -path[i].y() * CELL_SIZE));
            auto* item =
                new PointItem(pos.x(), pos.y(), kPathColor[1], 2);  // NOLINT
            item->setParentItem(m_pathItems);
        }
    }
    m_pathItems->setPath(pp);

    update();
}

void Scene::onPathChanged() {
    delete m_pathItems;
    m_pathItems = new QGraphicsPathItem();
    m_pathItems->setPen(QPen(kPathColor[0], 2));
    m_scene->addItem(m_pathItems);
    update();
}

void Scene::onPathSeted() {
    onPathChanged();
    espChanged();
}
