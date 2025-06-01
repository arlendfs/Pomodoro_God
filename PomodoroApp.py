import pytz
import streamlit as st
import sqlite3
import time
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="🍅 Pomodoro Timer Pro",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para animações e estilo
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #e74c3c;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    .timer-display {
        text-align: center;
        font-size: 4rem;
        font-weight: bold;
        color: #2c3e50;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 2rem 0;
        animation: glow 2s ease-in-out infinite alternate;
    }

    @keyframes glow {
        from { text-shadow: 0 0 20px #667eea; }
        to { text-shadow: 0 0 30px #764ba2; }
    }

    .status-text {
        text-align: center;
        font-size: 1.5rem;
        color: #34495e;
        margin-bottom: 2rem;
    }

    .session-counter {
        text-align: center;
        font-size: 1.2rem;
        color: #27ae60;
        font-weight: bold;
        background-color: #ecf0f1;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }

    .celebration {
        animation: bounce 1s ease infinite;
    }

    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
        40% { transform: translateY(-30px); }
        60% { transform: translateY(-15px); }
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    .digital-clock {
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 0.5rem;
        border: 2px solid #74b9ff;
        border-radius: 10px;
        margin-bottom: 1rem;
        font-family: 'Courier New', monospace;
    }
</style>


""", unsafe_allow_html=True)


class PomodoroApp:
    def __init__(self):
        self.setup_database()
        self.initialize_session_state()

    def setup_database(self):
        """Configura o banco de dados SQLite"""
        self.conn = sqlite3.connect('../pomodoro_stats.db', check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                session_type TEXT NOT NULL,
                duration INTEGER NOT NULL,
                completed BOOLEAN NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def initialize_session_state(self):
        """Inicializa o estado da sessão"""
        if 'work_time' not in st.session_state:
            st.session_state.work_time = 25 * 60  # 25 minutos
        if 'break_time' not in st.session_state:
            st.session_state.break_time = 5 * 60  # 5 minutos
        if 'long_break_time' not in st.session_state:
            st.session_state.long_break_time = 15 * 60  # 15 minutos
        if 'current_time' not in st.session_state:
            st.session_state.current_time = st.session_state.work_time
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        if 'is_paused' not in st.session_state:
            st.session_state.is_paused = False
        if 'is_work_session' not in st.session_state:
            st.session_state.is_work_session = True
        if 'session_count' not in st.session_state:
            st.session_state.session_count = 0
        if 'start_time' not in st.session_state:
            st.session_state.start_time = None
        if 'total_time' not in st.session_state:
            st.session_state.total_time = st.session_state.work_time
        if 'completed_sessions' not in st.session_state:
            st.session_state.completed_sessions = self.get_today_sessions()
        if 'celebration' not in st.session_state:
            st.session_state.celebration = False
        if 'last_update' not in st.session_state:
            st.session_state.last_update = time.time()

    @staticmethod
    def format_time(seconds):
        """Formata tempo em MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_today_sessions(self):
        """Obtém número de sessões completadas hoje"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('''
            SELECT COUNT(*) FROM sessions 
            WHERE date = ? AND completed = 1 AND session_type = 'work'
        ''', (today,))
        return self.cursor.fetchone()[0]

    def save_session(self, session_type, duration, completed):
        """Salva sessão no banco de dados"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute('''
            INSERT INTO sessions (date, session_type, duration, completed)
            VALUES (?, ?, ?, ?)
        ''', (today, session_type, duration, completed))
        self.conn.commit()

    def start_timer(self):
        """Inicia o timer"""
        if not st.session_state.is_running:
            st.session_state.is_running = True
            st.session_state.is_paused = False
            st.session_state.start_time = time.time()
            st.session_state.last_update = time.time()
            self.play_sound("start")

    def pause_timer(self):
        """Pausa o timer"""
        if st.session_state.is_running:
            st.session_state.is_paused = not st.session_state.is_paused
            if not st.session_state.is_paused:
                st.session_state.last_update = time.time()

    def stop_timer(self):
        """Para o timer"""
        if st.session_state.is_running or st.session_state.is_paused:
            # Salvar sessão como incompleta
            session_type = "work" if st.session_state.is_work_session else "break"
            elapsed = st.session_state.total_time - st.session_state.current_time
            self.save_session(session_type, elapsed, False)

            st.session_state.is_running = False
            st.session_state.is_paused = False
            st.session_state.current_time = st.session_state.work_time
            st.session_state.total_time = st.session_state.work_time
            st.session_state.is_work_session = True

    def complete_session(self):
        """Completa uma sessão"""
        session_type = "work" if st.session_state.is_work_session else "break"
        self.save_session(session_type, st.session_state.total_time, True)

        if st.session_state.is_work_session:
            st.session_state.session_count += 1
            st.session_state.completed_sessions += 1
            st.session_state.celebration = True
            self.play_sound("complete")
            self.show_notification("🎉 Sessão de trabalho completada! Hora da pausa!", "success")

            # Alternar para pausa
            if st.session_state.session_count % 4 == 0:
                st.session_state.current_time = st.session_state.long_break_time
                st.session_state.total_time = st.session_state.long_break_time
                self.show_notification("🏖️ Você merece uma pausa longa!", "info")
            else:
                st.session_state.current_time = st.session_state.break_time
                st.session_state.total_time = st.session_state.break_time
                self.show_notification("☕ Hora da pausa curta!", "info")
            st.session_state.is_work_session = False
        else:
            # Alternar para trabalho
            st.session_state.current_time = st.session_state.work_time
            st.session_state.total_time = st.session_state.work_time
            st.session_state.is_work_session = True
            self.play_sound("start")
            self.show_notification("💼 Pausa terminada! Hora de focar no trabalho!", "info")

        st.session_state.is_running = False
        st.session_state.is_paused = False

    def update_timer(self):
        """Atualiza o timer"""
        current_time = time.time()
        if st.session_state.is_running and not st.session_state.is_paused:
            elapsed = current_time - st.session_state.last_update
            if elapsed >= 1.0:  # Atualizar a cada segundo
                if st.session_state.current_time > 0:
                    st.session_state.current_time -= 1
                    st.session_state.last_update = current_time
                else:
                    self.complete_session()

    @staticmethod
    def play_sound(sound_type):
        """Reproduz som usando JavaScript"""
        if sound_type == "start":
            st.success("🎵 Timer iniciado!")

            # Som via JavaScript
            st.markdown("""
                <script>
                (function() {
                    try {
                        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        const oscillator = audioContext.createOscillator();
                        const gainNode = audioContext.createGain();

                        oscillator.connect(gainNode);
                        gainNode.connect(audioContext.destination);

                        oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
                        oscillator.type = 'sine';
                        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

                        oscillator.start(audioContext.currentTime);
                        oscillator.stop(audioContext.currentTime + 0.5);
                    } catch(e) {
                        console.log('Audio não suportado:', e);
                    }
                })();
                </script>
            """, unsafe_allow_html=True)

        elif sound_type == "complete":
            st.balloons()
            st.success("🎉 Sessão completada!")

            # Som de conclusão mais elaborado
            st.markdown("""
                <script>
                (function() {
                    try {
                        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        const frequencies = [523, 659, 784]; // C, E, G

                        frequencies.forEach((freq, index) => {
                            const oscillator = audioContext.createOscillator();
                            const gainNode = audioContext.createGain();

                            oscillator.connect(gainNode);
                            gainNode.connect(audioContext.destination);

                            oscillator.frequency.setValueAtTime(freq, audioContext.currentTime);
                            oscillator.type = 'sine';
                            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime + index * 0.2);
                            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + (index * 0.2) + 0.3);

                            oscillator.start(audioContext.currentTime + index * 0.2);
                            oscillator.stop(audioContext.currentTime + (index * 0.2) + 0.3);
                        });
                    } catch(e) {
                        console.log('Audio não suportado:', e);
                    }
                })();
                </script>
            """, unsafe_allow_html=True)

    @staticmethod
    def show_notification(message, notification_type="info"):
        """Exibe notificação na tela"""
        if notification_type == "success":
            st.success(message)
        elif notification_type == "warning":
            st.warning(message)
        elif notification_type == "error":
            st.error(message)
        else:
            st.info(message)

    def get_weekly_stats(self):
        """Obtém estatísticas da semana"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)

        self.cursor.execute('''
            SELECT date, session_type, COUNT(*) as count
            FROM sessions 
            WHERE date >= ? AND date <= ? AND completed = 1
            GROUP BY date, session_type
            ORDER BY date
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

        return self.cursor.fetchall()

    def get_daily_stats(self):
        """Obtém estatísticas do dia"""
        today = datetime.now().strftime('%Y-%m-%d')

        self.cursor.execute('''
            SELECT session_type, COUNT(*) as count, SUM(duration) as total_duration
            FROM sessions 
            WHERE date = ? AND completed = 1
            GROUP BY session_type
        ''', (today,))

        return self.cursor.fetchall()

    def create_progress_chart(self):
        """Cria gráfico de progresso semanal"""
        data = self.get_weekly_stats()

        if not data:
            st.info("📊 Sem dados para exibir. Complete algumas sessões para ver suas estatísticas!")
            return

        df = pd.DataFrame(data, columns=['date', 'session_type', 'count'])

        # Gráfico de barras
        fig = px.bar(df, x='date', y='count', color='session_type',
                     title='📈 Sessões Completadas nos Últimos 7 Dias',
                     labels={'count': 'Número de Sessões', 'date': 'Data'},
                     color_discrete_map={'work': '#e74c3c', 'break': '#3498db'})

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def create_daily_stats(self):
        """Cria estatísticas do dia atual"""
        stats = self.get_daily_stats()

        if not stats:
            st.info("📅 Nenhuma sessão completada hoje. Que tal começar agora?")
            return

        col1, col2 = st.columns(2)

        for session_type, count, total_duration in stats:
            hours = total_duration // 3600
            minutes = (total_duration % 3600) // 60

            if session_type == 'work':
                with col1:
                    st.metric(
                        label="💼 Sessões de Trabalho",
                        value=f"{count} sessões",
                        delta=f"{hours}h {minutes}m de foco"
                    )
            else:
                with col2:
                    st.metric(
                        label="☕ Pausas",
                        value=f"{count} pausas",
                        delta=f"{hours}h {minutes}m de descanso"
                    )

    def run(self):
        """Executa a aplicação principal"""
        # Cabeçalho
        celebration_class = "celebration" if st.session_state.celebration else ""
        st.markdown(f'<h1 class="main-header {celebration_class}">🍅 POMODORO TIMER PRO</h1>',
                    unsafe_allow_html=True)

        # Reset celebration
        if st.session_state.celebration:
            st.session_state.celebration = False

        # Layout principal
        col1, col2 = st.columns([2, 1])

        with col1:
            # Display do timer
            time_display = self.format_time(st.session_state.current_time)
            st.markdown(f'<div class="timer-display">{time_display}</div>',
                        unsafe_allow_html=True)

            # Status
            if st.session_state.is_work_session:
                status = "💼 Sessão de Trabalho" if st.session_state.is_running else "Pronto para trabalhar 💪"
                if st.session_state.session_count % 4 == 3 and st.session_state.session_count > 0:
                    status += " (Próxima: Pausa Longa)"
            else:
                if st.session_state.total_time == st.session_state.long_break_time:
                    status = "🏖️ Pausa Longa" if st.session_state.is_running else "Hora da pausa longa! 🏖️"
                else:
                    status = "☕ Pausa Curta" if st.session_state.is_running else "Hora da pausa! ☕"

            if st.session_state.is_paused:
                status = "⏸️ PAUSADO"

            st.markdown(f'<div class="status-text">{status}</div>', unsafe_allow_html=True)

            # Barra de progresso
            progress = 1 - (st.session_state.current_time / st.session_state.total_time)
            st.progress(progress)

            # Botões de controle
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

            with col_btn1:
                if st.button("▶️ INICIAR", type="primary", disabled=st.session_state.is_running):
                    self.start_timer()
                    self.show_notification("⏰ Timer iniciado! Foque no seu trabalho!", "success")
                    st.rerun()

            with col_btn2:
                pause_text = "▶️ CONTINUAR" if st.session_state.is_paused else "⏸️ PAUSAR"
                if st.button(pause_text, disabled=not st.session_state.is_running):
                    self.pause_timer()
                    if st.session_state.is_paused:
                        self.show_notification("⏸️ Timer pausado", "warning")
                    else:
                        self.show_notification("▶️ Timer retomado!", "info")
                    st.rerun()

            with col_btn3:
                if st.button("⏹️ PARAR", type="secondary"):
                    self.stop_timer()
                    self.show_notification("⏹️ Timer parado", "warning")
                    st.rerun()

            with col_btn4:
                if st.button("🔄 RESET"):
                    st.session_state.current_time = st.session_state.work_time
                    st.session_state.total_time = st.session_state.work_time
                    st.session_state.is_work_session = True
                    st.session_state.is_running = False
                    st.session_state.is_paused = False
                    self.show_notification("🔄 Timer resetado!", "info")
                    st.rerun()
        BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')
        with col2:

            # Relógio Digital
            current_time = datetime.now(BRAZIL_TZ)
            time_str = current_time.strftime("%H:%M:%S")
            date_str = current_time.strftime("%d/%m/%Y")

            st.markdown(f"""
                <div class="digital-clock">
                    <div class="current-time">
                        🕐 {time_str}<br>📅 {date_str}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Contador de sessões
            st.markdown(f'''
                <div class="session-counter">
                    🏆 Sessões Hoje: {st.session_state.completed_sessions}<br>
                    🔥 Total na Sessão: {st.session_state.session_count}
                </div>
            ''', unsafe_allow_html=True)

            # Configurações
            st.subheader("⚙️ Configurações")

            work_min = st.slider("Trabalho (min)", 1, 60, st.session_state.work_time // 60)
            break_min = st.slider("Pausa curta (min)", 1, 30, st.session_state.break_time // 60)
            long_break_min = st.slider("Pausa longa (min)", 1, 60, st.session_state.long_break_time // 60)

            if st.button("💾 Salvar Configurações"):
                st.session_state.work_time = work_min * 60
                st.session_state.break_time = break_min * 60
                st.session_state.long_break_time = long_break_min * 60

                if not st.session_state.is_running:
                    st.session_state.current_time = st.session_state.work_time
                    st.session_state.total_time = st.session_state.work_time

                st.success("✅ Configurações salvas!")
                st.rerun()

        # Estatísticas
        st.header("📊 Estatísticas")

        # Stats do dia
        st.subheader("📅 Hoje")
        self.create_daily_stats()

        # Gráfico semanal
        st.subheader("📈 Últimos 7 Dias")
        self.create_progress_chart()

        # Auto-atualização do timer e relógio
        if st.session_state.is_running and not st.session_state.is_paused:
            self.update_timer()
            time.sleep(0.1)  # Pequena pausa para evitar sobrecarga
            st.rerun()
        else:
            # Atualizar apenas o relógio quando timer não está rodando
            time.sleep(1)
            st.rerun()


# Executar aplicação
if __name__ == "__main__":
    app = PomodoroApp()
    app.run()