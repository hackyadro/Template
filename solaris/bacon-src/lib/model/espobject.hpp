#ifndef APP_ESPOBJECT_HPP
#define APP_ESPOBJECT_HPP
#include "abstractitem.hpp"


class EspObject : public AbstractItem {
public:
    explicit EspObject(const QString &title, const QPointF &pos) : AbstractItem(title, pos) {
    };
};

#endif
