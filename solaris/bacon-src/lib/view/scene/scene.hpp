#ifndef APP_SCENE_HPP
#define APP_SCENE_HPP

#include <QGraphicsView>
#include <QMainWindow>
#include <QVBoxLayout>
#include <QPropertyAnimation>

#include "espitem.hpp"
#include "model.hpp"

class PointItem;
class Scene : public QWidget {
    Q_OBJECT

   public:
    explicit Scene(Model* model, QWidget* parent = nullptr);

    ~Scene() override;

   protected:
    void keyPressEvent(QKeyEvent* event) override;

   private:
    Model* m_model;
    QGraphicsScene* m_scene;
    QGraphicsView* m_view;
    EspItem* m_esp;

    QVBoxLayout* m_layout;

    QList<PointItem*> m_items;

    void setupBasicScene();

    void clearScene();

    int m_zoomCounter = 0;

    QGraphicsPathItem* m_pathItems;

   public slots:
    void beaconChanged();

    void espChanged();

    void onPathChanged();

    void onPathSeted();
};

#endif  //APP_SCENE_HPP
