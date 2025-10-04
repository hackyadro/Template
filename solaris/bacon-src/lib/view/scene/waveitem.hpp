#ifndef APP_WAVEITEM_HPP
#define APP_WAVEITEM_HPP

#include <QGraphicsEllipseItem>
#include <QGraphicsItem>
#include <QTimer>
#include <QPainter>
#include <QLinearGradient>
#include <QBrush>
#include <QVector>

#include "const.hpp"

// Класс волн
class WaveItem : public QObject, public QGraphicsItem {
    Q_OBJECT

public:
    explicit WaveItem(
        qreal minRadius,
        qreal maxRadius,
        const QColor &first = kSecondaryColor[1],
        const QColor &second = kSecondaryColor[2],
        QGraphicsItem *parent = nullptr,
        int msec = 25, int delay = 0)
        : QGraphicsItem(parent),
          m_first(first),
          m_minRadius(minRadius),
          m_second(second),
          m_maxRadius(maxRadius),
          m_radius(0.0),
          m_timer(new QTimer(this)), m_msec(msec), m_delayTimer(new QTimer(this)) {
        connect(m_timer, &QTimer::timeout, this, &WaveItem::onUpdateTimer);
        connect(m_delayTimer, &QTimer::timeout, this, &WaveItem::startTimer);
        m_delayTimer->setSingleShot(true);
        m_delayTimer->start(delay);
    }

    QRectF boundingRect() const override {
        return QRectF(-m_maxRadius, -m_maxRadius,
                      m_maxRadius * 2, m_maxRadius * 2);
    }

    void paint(QPainter *painter, const QStyleOptionGraphicsItem *, QWidget *) override {
        auto radius = m_radius;
        if (m_radius <= m_minRadius) {
            radius = m_minRadius;
        }

        painter->setRenderHint(QPainter::Antialiasing, true);

        // Прозрачность уменьшается по мере расширения волны
        qreal alpha = 1.0 - (radius / m_maxRadius);
        m_first.setAlphaF(alpha);
        m_second.setAlphaF(0.0); // к внешнему краю волна исчезает

        QRadialGradient grad(QPointF(0, 0), radius);
        grad.setColorAt(0.0, m_first);
        grad.setColorAt(1.0, m_second);

        painter->setPen(QPen(m_first));
        painter->setBrush(grad);
        painter->drawEllipse(QPointF(0, 0), radius, radius);
    }

private slots:
    void onUpdateTimer() {
        m_radius += 1.0;
        if (m_radius > m_maxRadius)
            m_radius = 0.0;
        update();
    }

    void startTimer() {
        m_timer->start(m_msec);
    }

private:
    QColor m_first;
    QColor m_second;
    QTimer *m_timer;
    QTimer *m_delayTimer;
    qreal m_minRadius;
    qreal m_maxRadius;
    qreal m_radius;
    int m_msec;
};

#endif
