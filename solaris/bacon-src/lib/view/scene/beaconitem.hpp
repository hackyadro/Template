#ifndef APP_BEACONITEM_HPP
#define APP_BEACONITEM_HPP

#include <QGraphicsEllipseItem>
#include <QGraphicsSceneMouseEvent>
#include <QGraphicsRectItem>
#include <QGraphicsSimpleTextItem>
#include <QBrush>
#include <QString>
#include <QFont>

#include "const.hpp"

class BeaconItem : public QGraphicsEllipseItem {
public:
    BeaconItem(const QString &name, qreal x, qreal y, qreal radius = 12.0)
        : QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2),
          m_name(QString("%1\n(%2, %3)").arg(name).arg(x).arg(y)), m_x(x), m_y(y), m_radius(radius) {
        setPos(x * CELL_SIZE, -y * CELL_SIZE);
        setPen(Qt::NoPen);
        setBrush(QBrush(kSecondaryColor[0]));
        setZValue(7);

        // tooltip только для координат
        updateToolTip();

        // рамка с названием
        createLabel();

        // волны
        const auto msec = 70;
        const auto countWaves = 3;
        const auto r = radius * 7;
        for (int i = 0; i < countWaves; i++) {
            auto *waveItem = new WaveItem(
                radius,
                r,
                kSecondaryColor[0],
                kSecondaryColor[1],
                this,
                msec,
                r * i * msec / countWaves
            );
            waveItem->setZValue(6); // ниже рамки
            m_waves.push_back(waveItem);
        }
    }

    void setName(const QString &name) {
        m_name = name;
        updateToolTip();
        if (m_labelText) {
            m_labelText->setText(m_name);
            adjustLabelSize();
        }
    }

    QString name() const { return m_name; }

private:
    QString m_name;
    QList<WaveItem *> m_waves;
    qreal m_radius;
    qreal m_x;
    qreal m_y;

    QGraphicsRectItem *m_labelRect = nullptr;
    QGraphicsSimpleTextItem *m_labelText = nullptr;

    void updateToolTip() {
        setToolTip(QString("(%1, %2)").arg(m_x).arg(m_y));
    }

    void createLabel() {
        // Текст
        m_labelText = new QGraphicsSimpleTextItem(m_name, this);
        QFont font;
        font.setPointSize(10);
        font.setBold(true);
        m_labelText->setFont(font);
        m_labelText->setBrush(kTextLight);

        // Рамка
        m_labelRect = new QGraphicsRectItem(this);
        m_labelRect->setPen(QPen(kBgDark, 1));
        m_labelRect->setBrush(QColor(0, 0, 0, 120)); // полупрозрачный фон

        adjustLabelSize();
    }

    void adjustLabelSize() {
        if (!m_labelRect || !m_labelText) return;

        QRectF textRect = m_labelText->boundingRect();
        // Добавим поля
        const qreal margin = 4;
        const int m = 40;
        QRectF rect(margin * 2 + m / 2,
                    -margin * 2 - m,
                    textRect.width() + margin * 2,
                    textRect.height() + margin * 2);

        m_labelRect->setRect(rect);

        // Позиция текста внутри рамки
        m_labelText->setPos(rect.x() + margin, rect.y() + margin);
        m_labelRect->setZValue(11);
        m_labelText->setZValue(12);
    }
};

#endif
