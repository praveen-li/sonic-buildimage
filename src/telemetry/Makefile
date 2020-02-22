export GOPATH=/tmp/go

INSTALL := /usr/bin/install

all: sonic-telemetry

sonic-telemetry:
	/usr/local/go/bin/go get -v github.com/zhenggen-xu/sonic-telemetry/telemetry
	/usr/local/go/bin/go get -v github.com/zhenggen-xu/sonic-telemetry/dialout/dialout_client_cli
	rm -f -r node_exporter-0.18.1*
	wget https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz
	tar -xvf node_exporter-0.18.1.linux-amd64.tar.gz

install:
	$(INSTALL) -D ${GOPATH}/bin/telemetry $(DESTDIR)/usr/sbin/telemetry
	$(INSTALL) -D ${GOPATH}/bin/dialout_client_cli $(DESTDIR)/usr/sbin/dialout_client_cli
	$(INSTALL) -D node_exporter-0.18.1.linux-amd64/node_exporter $(DESTDIR)/usr/sbin/node_exporter

deinstall:
	rm $(DESTDIR)/usr/sbin/telemetry
	rm $(DESTDIR)/usr/sbin/dialout_client_cli
	rm $(DESTDIR)/usr/sbin/node_exporter

clean:
	rm -fr ${GOPATH}
