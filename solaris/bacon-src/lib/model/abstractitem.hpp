#ifndef APP_ABSTRACTITEM_HPP
#define APP_ABSTRACTITEM_HPP
#include <qpoint.h>
#include <qstring.h>


/**
 * Абстрактный объект на 2D карте (маяк или esp)
 */
class AbstractItem {
public:
    explicit AbstractItem(const QString &name, const QPointF &pos = QPointF()) : m_name(name), m_pos(pos) {
    }

    virtual ~AbstractItem() = default;

    QPointF pos() const {
        return m_pos;
    }

    QString name() const {
        return m_name;
    }

    /**
     * Заменяет позицию
     * @param pos Новая
     */
    void setPos(const QPointF &pos) {
        m_pos = pos;
    }

    /**
     * Передвижение точки.
     * @param delta изменение
     */
    void move(const QPointF &delta) {
        m_pos += delta;
    }

private:
    QString m_name;
    QPointF m_pos;
};


#endif //APP_ABSTRACTITEM_HPP
