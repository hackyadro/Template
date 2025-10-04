#ifndef APP_BEACON_HPP
#define APP_BEACON_HPP
#include "abstractitem.hpp"


class Beacon : public AbstractItem {
public:
    explicit Beacon(const QString &title, const QPointF &pos, const QString &macAddr,
                    bool isOnline = false) : AbstractItem(title, pos),
                                             m_macAddress(macAddr),
                                             m_isOnline(isOnline) {
    };

    bool isOnline() const { return m_isOnline; };

    void setIsOnline(bool isOnline) { m_isOnline = isOnline; };

    QString mac() const { return m_macAddress; };

    void setMac(const QString &mac) {
        m_macAddress = mac;
    }

private:
    QString m_macAddress;
    bool m_isOnline;
};

#endif //APP_BEACON_HPP
