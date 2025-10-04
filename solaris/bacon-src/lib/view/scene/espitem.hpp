#ifndef APP_ESPITEM_HPP
#define APP_ESPITEM_HPP

#include <QGraphicsEllipseItem>
#include <QPen>
#include <QVector>

#include "const.hpp"
#include "waveitem.hpp"

class EspItem : public QGraphicsEllipseItem {
   public:
    explicit EspItem(const QString& status, qreal radius = 8.0, qreal wave = 4,
                     int countWaves = 3)
        : QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2),
          m_radius(radius * wave),
          m_status(status) {
        setBrush(kPrimaryColor[0]);
        setPen(Qt::NoPen);
        setZValue(10);

        updateToolTip();
        createLabel();

        const auto msec = 100;
        for (int i = 0; i < countWaves; i++) {
            auto* waveItem = new WaveItem(radius, m_radius, kPrimaryColor[0],
                                          kPrimaryColor[2], this, msec,
                                          m_radius * i * msec / countWaves);
            waveItem->setZValue(9);
            m_waves.push_back(waveItem);
        }
    }

    ~EspItem() override {
        for (int i = 0; i < m_waves.size(); i++) {
            delete m_waves[i];
        }
    }

    QRectF boundingRect() const override {
        return QRectF(-m_radius, -m_radius, m_radius * 2, m_radius * 2);
    }

    void moveTo(const QPointF& p) { setPos(p); }

    void setStatus(const QString& status) {
        m_status = status;
        updateToolTip();
        if (m_labelText) {
            m_labelText->setText(QString("(%1, %2)\n%3")
                                     .arg(x() / CELL_SIZE)
                                     .arg(-y() / CELL_SIZE)
                                     .arg(m_status));
            adjustLabelSize();
        }
    }

    QString status() const { return m_status; }

    QGraphicsRectItem* m_labelRect = nullptr;
    QGraphicsSimpleTextItem* m_labelText = nullptr;

    void updateToolTip() { setToolTip(QString("(%1)").arg(m_status)); }

    void createLabel() {
        QString text = QString("(%1, %2)\n%3")
                           .arg(x() / CELL_SIZE)
                           .arg(-y() / CELL_SIZE)
                           .arg(m_status);
        m_labelText = new QGraphicsSimpleTextItem(text, this);
        QFont font;
        font.setPointSize(10);
        font.setBold(true);
        m_labelText->setFont(font);
        m_labelText->setBrush(kTextLight);

        // Рамка
        m_labelRect = new QGraphicsRectItem(this);
        m_labelRect->setPen(QPen(kGreen[0], 1));
        m_labelRect->setBrush(QColor(0, 0, 0, 120));  // полупрозрачный фон

        adjustLabelSize();
    }

    void adjustLabelSize() {
        if (!m_labelRect || !m_labelText)
            return;

        QRectF textRect = m_labelText->boundingRect();
        // Добавим поля
        const qreal margin = 4;
        const int m = 40;
        QRectF rect(margin * 2 + m / 2, -margin * 2 - m,
                    textRect.width() + margin * 2,
                    textRect.height() + margin * 2);

        m_labelRect->setRect(rect);

        // Позиция текста внутри рамки
        m_labelText->setPos(rect.x() + margin, rect.y() + margin);
        m_labelRect->setZValue(11);
        m_labelText->setZValue(12);
    }

   private:
    QList<WaveItem*> m_waves;
    qreal m_radius;
    QString m_status;
};

#endif  //APP_ESPITEM_HPP
