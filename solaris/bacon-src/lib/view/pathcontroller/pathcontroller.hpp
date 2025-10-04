#ifndef APP_PATHCONTROLLER_HPP
#define APP_PATHCONTROLLER_HPP

#include <qtmetamacros.h>
#include <QHeaderView>
#include <QList>
#include <QPoint>
#include <QStandardItemModel>
#include <QWidget>

#include "model.hpp"

QT_BEGIN_NAMESPACE
namespace Ui {
class PathController;
}
QT_END_NAMESPACE

class PathController : public QWidget {
    Q_OBJECT
   public:
    explicit PathController(Model* model, QWidget* parent = nullptr);
    ~PathController() override;

   private:
    Ui::PathController* m_ui;
    Model* m_model;

    QStandardItemModel* m_list;

   public slots:
    void setPath();
    void resetPath();
    void addPathPoint(const QPointF& pnt);
    void onUrlAccepted();
    void onFreqAccepted();
   signals:
    void urlChanged(const QString& url);
    void freqChanged(float freq);
    void pathReseted();
};

#endif
