import {ref, type Ref} from "vue";

export enum WSConnectionStatus {
	CONNECTING,
	OPEN,
	CLOSING,
	CLOSED
}
export abstract class ServiceWithWSBroadcast {
	protected ws: WebSocket;
	public readonly wsStatus: Ref<WSConnectionStatus> = ref(WSConnectionStatus.CONNECTING);
	private reconnectTimeout?: ReturnType<typeof setTimeout>;

	protected constructor(
		public readonly wsURL: string,
		protected readonly logPrefix: string
	) {
		this.log("Connecting...");
		this.ws = new WebSocket(this.wsURL);
		this.wsStatus.value = this.ws.readyState;
		this.setWSEventHandlers();
	}

	private setWSConn() {
		this.log("Connecting...");
		this.clearReconnect();
		this.ws = new WebSocket(this.wsURL);
		this.wsStatus.value = this.ws.readyState;
	}

	private setWSEventHandlers() {
		this.log("Setting event handlers");

		this.ws.onopen = () => {
			this.log("Connected");
			this.wsStatus.value = this.ws.readyState;
		};

		this.ws.onerror = e => {
			this.error("Error", e);
			this.wsStatus.value = this.ws.readyState;
			this.setReconnect();
		};

		this.ws.onclose = e => {
			this.warn("Connection closed", e);
			this.wsStatus.value = this.ws.readyState;
			this.setReconnect();
		};
		this.ws.onmessage = this.msgReact.bind(this);
	}

	protected setWS() {
		this.setWSConn();
		this.setWSEventHandlers();
	}

	protected clearReconnect() {
		if(this.reconnectTimeout)
			clearTimeout(this.reconnectTimeout);
		this.reconnectTimeout = undefined;
	}

	protected setReconnect() {
		this.clearReconnect();
		this.reconnectTimeout = setTimeout(()=>{
			this.setWS();
		}, 3000);
	}

	public log(...data: any[]) {
		console.log(this.logPrefix, ...data);
	}

	public warn(...data: any[]){
		console.warn(this.logPrefix, ...data);
	}

	public error(...data: any[]){
		console.error(this.logPrefix, ...data);
	}

	protected abstract msgReact(event: MessageEvent<any>): void;
}
