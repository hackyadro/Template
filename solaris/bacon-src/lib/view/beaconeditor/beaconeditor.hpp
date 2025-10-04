#ifndef APP_BEACONEDITOR_HPP
#define APP_BEACONEDITOR_HPP

#include <QWidget>

#include "beacon.hpp"
#include "model.hpp"


QT_BEGIN_NAMESPACE

namespace Ui {
    class BeaconEditor;
}

QT_END_NAMESPACE


class BeaconEditor : public QWidget {
    Q_OBJECT

public:
    explicit BeaconEditor(Model *m, QWidget *parent = nullptr);

    ~BeaconEditor() override;

private:
    Ui::BeaconEditor *m_ui;
    Model *m_model;

    QList<Beacon> m_beacons;
    void parseBeacons(const QString &text);

public slots:
    void setText(const QString &text);
    void updateText();
    void updateBeacons();
    void openFile();
    void saveIntoFile();
    void acceptedSlot();

signals:
    void accepted(const QList<Beacon> &beacons);
};


#endif //APP_BEACONEDITOR_HPP
