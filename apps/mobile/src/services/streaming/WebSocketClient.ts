import { PositionUpdate } from "../../domain/models/PositionUpdate";
import { LetterStatusUpdate } from "../../domain/models/LetterStatus";
import { TajweedGradeUpdate } from "../../domain/models/TajweedStatus";
import { RecitationErrorUpdate } from "../../domain/models/RecitationError";
import { WordStatusUpdate } from "../../domain/models/WordStatus";

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY_MS = 1000;

interface ServerMessage {
  type: string;
  surah_id?: number;
  ayah_number?: number;
  word_index?: number;
  confidence?: number;
  text?: string;
  message?: string;
  is_partial?: boolean;
  next_surah_id?: number | null;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = "";
  private intentionalClose = false;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  onPositionUpdate: ((update: PositionUpdate) => void) | null = null;
  onConnectionChange: ((state: ConnectionState) => void) | null = null;
  onError: ((message: string) => void) | null = null;
  onAyahStarted: ((surahId: number, ayahNumber: number, text: string) => void) | null = null;
  onAyahCompleted: ((surahId: number, ayahNumber: number) => void) | null = null;
  onLetterStatusUpdate: ((update: LetterStatusUpdate) => void) | null = null;
  onTajweedStatusUpdate: ((update: TajweedGradeUpdate) => void) | null = null;
  onSessionReady: (() => void) | null = null;
  onRecitationError: ((update: RecitationErrorUpdate) => void) | null = null;
  onWordStatusUpdate: ((update: WordStatusUpdate) => void) | null = null;
  onSurahCompleted: ((surahId: number, nextSurahId: number | null) => void) | null = null;

  connect(url: string) {
    this.url = url;
    this.intentionalClose = false;
    this.reconnectAttempts = 0;
    this.clearReconnectTimer();
    this.openConnection();
  }

  disconnect() {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendAudioChunk(chunk: ArrayBuffer) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(chunk);
    }
  }

  sendControl(msg: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private openConnection() {
    console.log(`[WS] Connecting to: ${this.url}`);
    this.onConnectionChange?.("connecting");

    this.ws = new WebSocket(this.url);
    this.ws.binaryType = "arraybuffer";

    this.ws.onopen = () => {
      console.log(`[WS] Connected to: ${this.url}`);
      this.reconnectAttempts = 0;
      this.onConnectionChange?.("connected");
    };

    this.ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === "string") {
        this.handleTextMessage(event.data);
      }
    };

    this.ws.onerror = (event: Event) => {
      console.error(`[WS] Error on ${this.url}:`, (event as any).message ?? "unknown error");
      if (!this.intentionalClose) {
        this.onError?.("WebSocket connection error");
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      console.log(`[WS] Closed: code=${event.code} reason="${event.reason}" url=${this.url}`);
      this.ws = null;
      if (this.intentionalClose) {
        this.onConnectionChange?.("disconnected");
        return;
      }

      if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        this.scheduleReconnect();
      } else {
        console.error(`[WS] Giving up after ${MAX_RECONNECT_ATTEMPTS} reconnect attempts to ${this.url}`);
        this.onError?.("Connection lost after multiple retries");
        this.onConnectionChange?.("error");
      }
    };
  }

  private scheduleReconnect() {
    const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;
    console.log(`[WS] Reconnect attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${delay}ms to ${this.url}`);
    this.onConnectionChange?.("connecting");
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.openConnection();
    }, delay);
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private handleTextMessage(data: string) {
    try {
      const msg: ServerMessage = JSON.parse(data);
      console.log("[WS ←]", msg.type, JSON.stringify(msg));

      if (msg.type === "batch") {
        const batchMessages = (msg as any).messages;
        if (Array.isArray(batchMessages)) {
          for (const inner of batchMessages) {
            this.handleSingleMessage(inner);
          }
        }
        return;
      }

      this.handleSingleMessage(msg);
    } catch (e) {
      console.error("[WS ←] parse error:", e, data.substring(0, 200));
      this.onError?.("Failed to parse server message");
    }
  }

  private handleSingleMessage(msg: ServerMessage) {
      switch (msg.type) {
        case "position":
          if (
            msg.surah_id != null &&
            msg.ayah_number != null &&
            msg.word_index != null
          ) {
            this.onPositionUpdate?.({
              surahId: msg.surah_id,
              ayahNumber: msg.ayah_number,
              wordIndex: msg.word_index,
              confidence: msg.confidence ?? 0,
            });
          }
          break;

        case "ayah.started":
          if (msg.surah_id != null && msg.ayah_number != null) {
            this.onAyahStarted?.(msg.surah_id, msg.ayah_number, msg.text ?? "");
          }
          break;

        case "ayah.completed":
          if (msg.surah_id != null && msg.ayah_number != null) {
            this.onAyahCompleted?.(msg.surah_id, msg.ayah_number);
          }
          break;

        case "letter.status":
          if (msg.surah_id != null && msg.ayah_number != null) {
            const raw = (msg as any).updates;
            if (Array.isArray(raw)) {
              console.log("[WS ←] letter.status updates:", raw.length, "ayah:", msg.ayah_number);
              this.onLetterStatusUpdate?.({
                surahId: msg.surah_id,
                ayahNumber: msg.ayah_number,
                updates: raw.map((u: any) => ({
                  wordIndex: u.word_index,
                  letterIndex: u.letter_index,
                  status: u.status,
                })),
                confidence: msg.confidence ?? 0,
              });
            }
          }
          break;

        case "tajweed.status":
          if (msg.surah_id != null && msg.ayah_number != null) {
            const tajweedRaw = (msg as any).updates;
            if (Array.isArray(tajweedRaw)) {
              this.onTajweedStatusUpdate?.({
                surahId: msg.surah_id,
                ayahNumber: msg.ayah_number,
                updates: tajweedRaw.map((u: any) => ({
                  wordIndex: u.word_index,
                  letterIndex: u.letter_index,
                  rule: u.rule,
                  grade: u.grade,
                })),
              });
            }
          }
          break;

        case "recitation.error":
          if (msg.surah_id != null && msg.ayah_number != null) {
            const errorRaw = (msg as any).errors;
            if (Array.isArray(errorRaw)) {
              this.onRecitationError?.({
                surahId: msg.surah_id,
                ayahNumber: msg.ayah_number,
                errors: errorRaw.map((e: any) => ({
                  errorType: e.error_type,
                  speechErrorType: e.speech_error_type,
                  expectedPhoneme: e.expected_phoneme,
                  predictedPhoneme: e.predicted_phoneme,
                  uthmaniStart: e.uthmani_start,
                  uthmaniEnd: e.uthmani_end,
                  tajweedRule: e.tajweed_rule ?? null,
                  expectedLen: e.expected_len ?? null,
                  predictedLen: e.predicted_len ?? null,
                })),
              });
            }
          }
          break;

        case "word.status":
          if (msg.surah_id != null && msg.ayah_number != null) {
            const wordRaw = (msg as any).updates;
            if (Array.isArray(wordRaw)) {
              this.onWordStatusUpdate?.({
                surahId: msg.surah_id,
                ayahNumber: msg.ayah_number,
                updates: wordRaw.map((u: any) => ({
                  wordIndex: u.word_index,
                  status: u.status,
                  confidence: u.confidence,
                  tajweedGrade: u.tajweed_grade ?? null,
                })),
              });
            }
          }
          break;

        case "surah.completed":
          if (msg.surah_id != null) {
            this.onSurahCompleted?.(msg.surah_id, msg.next_surah_id ?? null);
          }
          break;

        case "session.ready":
          this.onSessionReady?.();
          break;

        case "error":
          this.onError?.(msg.message ?? "Unknown server error");
          break;

        default:
          console.log("[WS ←] unhandled type:", msg.type);
          break;
      }
  }
}
