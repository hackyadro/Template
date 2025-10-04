#ifndef APP_MODEL_HPP
#define APP_MODEL_HPP
#include <QList>
#include <QObject>

#include "beacon.hpp"
#include "espobject.hpp"
#include "mqtt_connector/mqtt_client.h"

class Model : public QObject {
    Q_OBJECT

   public:
    explicit Model(mqtt_connector::MqttClient* connector);

    [[nodiscard]] QList<Beacon> beacons() const;

    [[nodiscard]] Beacon beacon(int index) const;

    [[nodiscard]] EspObject esp() const;

    void setPosEsp(const QPointF& pos);

    void moveEsp(const QPointF& pos);

    void clearPath();

    void addPointToPath(const QPointF& pos);

    [[nodiscard]] QList<QPointF> path() const;

    void updateBeacon(int index, const Beacon& beacon);

    void addBeacon(const Beacon& beacon);

    [[nodiscard]] QString status() const;

   signals:
    void dataChanged();
    void pointAddedSignal(const QPointF& pnt);

    void pathChanged();

    void oneBeaconChanged(int index);

    void signalBeaconsChanged(const QList<QPair<QString, QPointF>> &newBeacons);

    void freqChanged(float f);

    void urlChanged(const QString& url);

    void satPath();

   private:
    QList<Beacon> m_beacons;
    EspObject m_esp;
    QList<QPointF> m_path;
    QString m_url;
    QString m_status = "None";
    float m_freq;

    bool m_running = false;

    mqtt_connector::MqttClient* m_connector;

   public slots:
    void beaconChanged(const QList<Beacon>& beacons);
    void pointAdded(const QPointF& point);
    void onChangeFreq(float freq);
    void onUrlChanged(const QString& url);
    void setPath(const QList<QPointF>& path);

    void onStopped();
    void onStarted();

    void onResetPath();

    void onStatusChanged(const QString& status);
};

#endif  //APP_MODEL_HPP
