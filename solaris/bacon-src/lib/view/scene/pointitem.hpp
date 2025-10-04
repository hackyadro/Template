#ifndef APP_POINTITEM_HPP
#define APP_POINTITEM_HPP

#include <QGraphicsSimpleTextItem>
#include <QBrush>
#include <QFont>

#include "const.hpp"

class PointItem : public QGraphicsEllipseItem {
public:
    PointItem(qreal x, qreal y, const QColor &color = kPathColor[1], qreal radius = 10.0)
        : QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2) {
        setPos(x * CELL_SIZE, -y * CELL_SIZE);
        setPen(Qt::NoPen);
        setBrush(QBrush(color));
        setZValue(7);
    }
};

#endif
