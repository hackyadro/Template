#ifndef APP_GRIDITEM_HPP
#define APP_GRIDITEM_HPP

#include <QGraphicsItem>
#include <QPen>

class GridItem : public QGraphicsItem {
public:
    GridItem(qreal spacing = 50.0, QGraphicsItem *parent = nullptr)
        : QGraphicsItem(parent), m_spacing(spacing) {
        setZValue(-100); // сетка всегда позади
    }

    QRectF boundingRect() const override {
        // Ограничим сетку разумным квадратом
        return QRectF(-COUNT_CELLS * CELL_SIZE, -COUNT_CELLS * CELL_SIZE, COUNT_CELLS * 2 * CELL_SIZE,
                      COUNT_CELLS * 2 * CELL_SIZE);
    }

    void paint(QPainter *painter, const QStyleOptionGraphicsItem *, QWidget *) override {
        painter->setPen(QPen(kGridColor, 0));
        const QRectF rect = boundingRect();

        for (qreal x = rect.left(); x <= rect.right(); x += m_spacing)
            painter->drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()));

        for (qreal y = rect.top(); y <= rect.bottom(); y += m_spacing)
            painter->drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y));
    }

private:
    qreal m_spacing;
};


#endif //APP_GRIDITEM_HPP
