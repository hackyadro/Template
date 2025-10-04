#include "model.hpp"

#include <iostream>

Model::Model(mqtt_connector::MqttClient* connector)
    : m_esp(QString("esp"), QPointF(10.0, 10.0)), m_connector(connector) {}

QList<Beacon> Model::beacons() const {
    return m_beacons;
}

Beacon Model::beacon(int index) const {
    return m_beacons.at(index);
}

EspObject Model::esp() const {
    return m_esp;
}

void Model::setPosEsp(const QPointF& pos) {
    m_esp.setPos(pos);
}

void Model::moveEsp(const QPointF& pos) {
    m_esp.move(pos);
}

void Model::clearPath() {
    m_path.clear();
}

void Model::addPointToPath(const QPointF& pos) {
    if (!m_running) {
        return;
    }
    QPointF p = pos;
    m_path.append(p);
    m_esp.setPos(p);
    emit dataChanged();
    emit pointAddedSignal(p);
}

QList<QPointF> Model::path() const {
    return m_path;
}

void Model::updateBeacon(int index, const Beacon& beacon) {
    m_beacons[index] = beacon;
    QList<QPair<QString, QPointF>> newBeacons;
    for (int i = 0; i < m_beacons.size(); ++i) {
        newBeacons.append({m_beacons[i].name(), m_beacons[i].pos()});
    }
    emit signalBeaconsChanged(newBeacons);
}

void Model::addBeacon(const Beacon& beacon) {
    m_beacons.append(beacon);
    QList<QPair<QString, QPointF>> newBeacons;
    for (int i = 0; i < m_beacons.size(); ++i) {
        newBeacons.append({m_beacons[i].name(), m_beacons[i].pos()});
    }
    emit signalBeaconsChanged(newBeacons);
}

QString Model::status() const {
    return m_status;
}

void Model::beaconChanged(const QList<Beacon>& beacons) {
    m_beacons = beacons;
    QList<QPair<QString, QPointF>> newBeacons;
    for (int i = 0; i < m_beacons.size(); ++i) {
        newBeacons.append({m_beacons[i].name(), m_beacons[i].pos()});
    }
    emit signalBeaconsChanged(newBeacons);
}

void Model::pointAdded(const QPointF& point) {
    if (!m_running) {
        return;
    }
    m_path.append(point);
    emit pathChanged();
}

void Model::onChangeFreq(float freq) {
    m_freq = freq;
    emit freqChanged(m_freq);
}

void Model::onUrlChanged(const QString& url) {
    m_url = url;
    emit urlChanged(m_url);
}

void Model::setPath(const QList<QPointF>& path) {
    m_path = path;
    emit satPath();
}

void Model::onStopped() {
    std::cout << "stopped\n";
    m_running = false;
}

void Model::onStarted() {
    std::cout << "started\n";
    m_running = true;
}

void Model::onResetPath() {
    m_path.clear();
    emit pathChanged();
}

void Model::onStatusChanged(const QString& status) {
    m_status = status;
}
