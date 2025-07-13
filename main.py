# -*- coding: utf-8 -*-
# Importaciones necesarias para la aplicación Kivy
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen # Importar ScreenManager y Screen para la navegación
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle # Importar Rectangle para la sombra de la imagen

import requests
import threading
import json
import os # Para verificar si la fuente existe
import sys # Para PyInstaller
from kivy.resources import resource_add_path, resource_find # Para gestión de recursos en Kivy

# Determina si la aplicación se está ejecutando como un ejecutable empaquetado por PyInstaller.
# Si es así, añade la ruta temporal donde PyInstaller extrae los recursos.
if hasattr(sys, '_MEIPASS'):
    resource_add_path(sys._MEIPASS)
else:
    # Si se ejecuta como script normal, añade la ruta del directorio actual.
    resource_add_path(os.path.dirname(os.path.abspath(__file__)))


# Establece el tamaño de ventana por defecto para simular una app móvil o escritorio
Window.size = (400, 600) # Altura de la ventana ajustada para más contenido
Window.clearcolor = (0, 0, 0, 1) # Fondo negro (RGBA)


# Cargar fuentes Poppins
# Asegúrate de que estos archivos .ttf estén en el mismo directorio que tu script
# O especifica la ruta completa
FONT_BOLD = 'Poppins-SemiBold.ttf' # O el nombre del archivo de la fuente semibold
FONT_REGULAR = 'Poppins-Regular.ttf' # O el nombre del archivo del archivo de la fuente regular

# Verificar si las fuentes existen, si no, usar la fuente por defecto de Kivy
if not os.path.exists(resource_find(FONT_BOLD) if resource_find(FONT_BOLD) else FONT_BOLD):
    FONT_BOLD = None
    print(f"Advertencia: No se encontró la fuente '{FONT_BOLD}'. Se usará la fuente por defecto de Kivy.")
if not os.path.exists(resource_find(FONT_REGULAR) if resource_find(FONT_REGULAR) else FONT_REGULAR):
    FONT_REGULAR = None
    print(f"Advertencia: No se encontró la fuente '{FONT_REGULAR}'. Se usará la fuente por defecto de Kivy.")


class RoundedShadowButton(Button):
    """
    Botón personalizado con bordes redondeados y una sombra.
    La sombra se ajusta ligeramente al presionar el botón para un efecto.
    """
    button_radius = ListProperty([dp(12)]) # Radio de las esquinas del botón
    shadow_radius = ListProperty([0]) # Radio de las esquinas de la sombra (cuadrada)
    shadow_offset_x = NumericProperty(dp(3)) # Desplazamiento horizontal de la sombra
    shadow_offset_y = NumericProperty(dp(3)) # Desplazamiento vertical de la sombra
    shadow_color = ListProperty([1, 1, 1, 1]) # Color blanco con 100% de opacidad para la sombra
    shadow_spread = NumericProperty(dp(2)) # Cuánto más grande es la sombra que el botón

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.bind(pos=self.update_canvas_instructions,
                  size=self.update_canvas_instructions,
                  state=self.update_canvas_instructions) # ¡Vincular también a 'state' para el efecto!
        self.update_canvas_instructions()

    def update_canvas_instructions(self, *args):
        """
        Actualiza las instrucciones de dibujo en el canvas del botón,
        aplicando un efecto cuando el botón está presionado.
        """
        self.canvas.before.clear()
        with self.canvas.before:
            current_shadow_offset_y = self.shadow_offset_y
            current_shadow_color = list(self.shadow_color) # Copia para modificar opacidad

            # Efecto al presionar: la sombra se mueve hacia arriba (o el botón hacia abajo)
            if self.state == 'down':
                current_shadow_offset_y = dp(1) # Sombra más cerca del botón
                current_shadow_color[3] = 0.5 # Sombra un poco menos opaca
            else:
                current_shadow_offset_y = self.shadow_offset_y # Vuelve al offset normal
                current_shadow_color[3] = 1.0 # Vuelve a la opacidad normal

            # Dibujar la sombra
            Color(*current_shadow_color)
            if all(r == 0 for r in self.shadow_radius):
                Rectangle(
                    pos=(self.x - self.shadow_spread + self.shadow_offset_x,
                         self.y - self.shadow_spread - current_shadow_offset_y),
                    size=(self.width + 2 * self.shadow_spread,
                          self.height + 2 * self.shadow_spread)
                )
            else:
                RoundedRectangle(
                    pos=(self.x - self.shadow_spread + self.shadow_offset_x,
                         self.y - self.shadow_spread - current_shadow_offset_y),
                    size=(self.width + 2 * self.shadow_spread,
                          self.height + 2 * self.shadow_spread),
                    radius=self.button_radius
                )
            # Dibujar el fondo principal del botón
            Color(*self.background_color)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=self.button_radius
            )


class LoadingScreen(Screen):
    """
    Nueva pantalla de carga que se muestra al inicio.
    """
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = 'loading'
        self.setup_ui()

    def setup_ui(self):
        # Se elimina el Label de "Cargando..." para quitar el mensaje.
        layout = BoxLayout(orientation='vertical',
                           padding=dp(20))
        layout.pos_hint = {'center_x': 0.5, 'center_y': 0.5} # Centrar el contenido
        # No se añade ningún widget al layout para esta pantalla, ya que el usuario pidió quitar el "cargando".
        self.add_widget(layout)


class MainScreen(Screen):
    """
    Pantalla principal de la aplicación.
    Permite al usuario ingresar una cantidad en USD y muestra una frase motivacional.
    """
    motivational_quote_text = StringProperty("Cargando frase motivacional...")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = 'main'
        self.app = App.get_running_app()
        self.setup_ui()
        # ELIMINADO: Las llamadas a Clock.schedule_once para fetching se moverán a ConverterApp.start_app_init_tasks
        # Iniciar la carga de la frase motivacional al inicio
        # Clock.schedule_once(self.app.fetch_motivational_quote, 0)
        # Iniciar la carga de tasas (BCV se usa en la 2da pantalla)
        # Clock.schedule_once(self.app.fetch_rates, 0)

    def setup_ui(self):
        """Configura la interfaz de usuario de la pantalla principal."""
        # BoxLayout principal que contendrá todos los elementos
        main_content_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(0), # Espaciado entre elementos del layout
                                        size_hint=(0.9, None)) # Ancho 90%, altura automática (se ajusta al contenido)
        # CAMBIO: Ajustar pos_hint para bajar todos los elementos de la pantalla principal
        main_content_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.19}

        # Imagen de la moneda
        image_source = 'icono_moneda.png'
        try:
            if not resource_find(image_source):
                print(f"ERROR: La imagen '{image_source}' no se encontró. Se usará un placeholder.")
                image_source = 'https://placehold.co/100x100/gold/white?text=$'
            else:
                print(f"DEBUG: Intentando cargar imagen desde: {resource_find(image_source)}")

            coin_image = Image(source=image_source,
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})

        except Exception as e:
            print(f"ERROR: No se pudo cargar la imagen '{image_source}'. Error: {e}")
            coin_image = Image(source='https://placehold.co/100x100/gold/white?text=$',
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})

        main_content_layout.add_widget(coin_image)

        # Label para la frase motivacional
        font_name_label = FONT_REGULAR if FONT_REGULAR else 'Roboto'
        self.motivational_quote_label = Label(text=self.motivational_quote_text,
                                              font_size=dp(14),
                                              color=(1,1,1,1),
                                              halign='center', valign='middle',
                                              size_hint=(None, None), size=(dp(280), dp(100)),
                                              pos_hint={'center_x': 0.5},
                                              text_size=(dp(280), None),
                                              font_name=font_name_label)
        main_content_layout.add_widget(self.motivational_quote_label)

        # Espaciador entre la frase y el input (espacio de 15dp)
        main_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(15)))

        # Input para la cantidad en USD
        self.usd_input = TextInput(hint_text='Valor USD a convertir', font_size=dp(18),
                                   foreground_color=(1, 1, 1, 1),
                                   hint_text_color=(0.7, 0.7, 0.7, 1),
                                   background_color=(0.1, 0.1, 0.1, 1),
                                   padding=[dp(20), dp(12), dp(20), dp(12)],
                                   size_hint=(None, None), size=(dp(280), dp(50)),
                                   pos_hint={'center_x': 0.5},
                                   multiline=False, input_type='number',
                                   cursor_color=(1,1,1,1),
                                   font_name=FONT_BOLD if FONT_BOLD else 'Roboto')
        main_content_layout.add_widget(self.usd_input)

        # Espaciador entre el input y el botón (espacio de 10dp)
        main_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        # Botón Convertir (usando la clase RoundedShadowButton) - USD a VES
        convert_usd_button = RoundedShadowButton(text='Convertir USD a VES', font_size=dp(20),
                                background_color=(0.1, 0.1, 0.1, 1),
                                color=(1, 1, 1, 1),
                                size_hint=(None, None), size=(dp(280), dp(50)),
                                pos_hint={'center_x': 0.5},
                                on_press=self.convert_currency, # Este es para USD a VES
                                font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                                button_radius=[dp(12)] * 4,
                                shadow_radius=[0] * 4,
                                shadow_offset_x=dp(3),
                                shadow_offset_y=dp(3),
                                shadow_color=[1, 1, 1, 1],
                                shadow_spread=dp(2)
                                )
        main_content_layout.add_widget(convert_usd_button)

        # Espaciador entre los botones
        main_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

        # Botón para ir a la pantalla de conversión VES a USD
        go_to_ves_usd_button = RoundedShadowButton(text='Convertir VES a USD', font_size=dp(20),
                                background_color=(0.1, 0.1, 0.1, 1),
                                color=(1, 1, 1, 1),
                                size_hint=(None, None), size=(dp(280), dp(50)),
                                pos_hint={'center_x': 0.5},
                                on_press=self.go_to_ves_usd_screen,
                                font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                                button_radius=[dp(12)] * 4,
                                shadow_radius=[0] * 4,
                                shadow_offset_x=dp(3),
                                shadow_offset_y=dp(3),
                                shadow_color=[1, 1, 1, 1],
                                shadow_spread=dp(2)
                                )
        main_content_layout.add_widget(go_to_ves_usd_button)

        # Espaciador entre los botones (nuevo)
        main_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

        # CAMBIO: Botón "Ver tasa BCV de hoy" movido a la última posición
        view_bcv_rate_button = RoundedShadowButton(text='Ver tasa BCV de hoy', font_size=dp(20),
                                background_color=(0.1, 0.1, 0.1, 1),
                                color=(1, 1, 1, 1),
                                size_hint=(None, None), size=(dp(280), dp(50)),
                                pos_hint={'center_x': 0.5},
                                on_press=self.view_bcv_rate_today,
                                font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                                button_radius=[dp(12)] * 4,
                                shadow_radius=[0] * 4,
                                shadow_offset_x=dp(3),
                                shadow_offset_y=dp(3),
                                shadow_color=[1, 1, 1, 1],
                                shadow_spread=dp(2)
                                )
        main_content_layout.add_widget(view_bcv_rate_button)


        self.add_widget(main_content_layout) # Añadir el layout de contenido a la pantalla


    def on_motivational_quote_text(self, instance, value):
        """
        Este método se llama automáticamente cuando la propiedad motivational_quote_text de MainScreen cambia.
        Asegura que el Label se actualice visualmente.
        """
        self.motivational_quote_label.text = value
        print(f"DEBUG (MainScreen.on_motivational_quote_text): Label text updated to: '{value}'")


    def on_pre_enter(self, *args):
        """
        Se llama justo antes de que la pantalla se haga activa.
        Asegura que la frase motivacional se muestre actualizada o se vuelva a cargar.
        """
        print(f"DEBUG (MainScreen.on_pre_enter): Current phrase in MainScreen (before possible update): '{self.motivational_quote_text}'")
        # El mensaje de "Cargando frase motivacional..." o el de fallback se maneja ahora desde la App
        # No es necesario recargar aquí a menos que sea el mensaje inicial "Cargando..."
        if self.app.motivational_quote_text == "Cargando frase motivacional...":
            print("DEBUG (MainScreen.on_pre_enter): Phrase in App is initial placeholder, attempting to reload.")
            Clock.schedule_once(self.app.fetch_motivational_quote, 0)
        # Si el mensaje es el de fallback, no se intenta recargar aquí para evitar loops
        # Se asume que el fallback ya es la frase deseada por el usuario.

        self.motivational_quote_text = self.app.motivational_quote_text
        print(f"DEBUG (MainScreen.on_pre_enter): Phrase in MainScreen (after possible update): '{self.motivational_quote_text}'")


    def convert_currency(self, instance):
        """
        Maneja la lógica de conversión cuando se presiona el botón 'Convertir USD a VES'.
        Pasa a la pantalla de resultados y muestra la conversión.
        """
        try:
            usd_amount = float(self.usd_input.text)
            self.app.usd_amount = usd_amount # Guarda el monto USD en la app
            self.manager.current = 'result'
        except ValueError:
            print("Por favor, ingrese un número válido.")
            self.usd_input.text = ""
            self.usd_input.hint_text = "¡Error! Ingrese un número."

    def view_bcv_rate_today(self, instance):
        """
        Maneja la lógica para ver la tasa BCV de hoy (1 USD a VES).
        Establece usd_amount a 1 y navega a la pantalla de resultados.
        """
        self.app.usd_amount = 1.0 # Establece el monto a 1 USD
        self.manager.current = 'result'

    def go_to_ves_usd_screen(self, instance):
        """
        Cambia a la pantalla de conversión de VES a USD.
        """
        self.manager.current = 'ves_to_usd'


class ResultScreen(Screen):
    """
    Pantalla de resultados.
    Muestra el monto en USD y su equivalente en Bolívar (Bs) usando la tasa BCV.
    """
    bcv_rate_text = StringProperty("Tasa BCV hoy: No disponible") # Cambiado el texto inicial

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = 'result'
        self.app = App.get_running_app()
        self.setup_ui()

    def setup_ui(self):
        """Configura la interfaz de usuario de la pantalla de resultados."""
        # BoxLayout principal que contendrá todos los elementos
        # Se cambia spacing a 0 para controlar los espacios manualmente
        result_content_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(0),
                                          size_hint=(0.9, None))
        # CAMBIO REALIZADO: Ajustar center_y para subir el contenido y dejar espacio para la imagen y la tasa.
        result_content_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.35}

        # Imagen de la moneda
        image_source = 'icono_moneda.png'
        try:
            if not resource_find(image_source):
                print(f"ERROR: La imagen '{image_source}' no se encontró. Se usará un placeholder.")
                image_source = 'https://placehold.co/100x100/gold/white?text=$'
            else:
                print(f"DEBUG: Intentando cargar imagen desde: {resource_find(image_source)}")

            coin_image = Image(source=image_source,
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})

        except Exception as e:
            print(f"ERROR: No se pudo cargar la imagen '{image_source}'. Error: {e}")
            coin_image = Image(source='https://placehold.co/100x100/gold/white?text=$',
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})
        result_content_layout.add_widget(coin_image)

        # Espaciador explícito entre la imagen y la tasa BCV (antes era implícito por spacing=10)
        result_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        # Contenedor para la tasa BCV (siempre visible)
        font_name_label = FONT_REGULAR if FONT_REGULAR else 'Roboto'
        rate_font_size = dp(18)

        self.bcv_rate_label = Label(text=self.bcv_rate_text, font_size=rate_font_size, color=(1,1,1,1),
                                     halign='center', valign='middle', size_hint_x=1,
                                     size_hint_y=None, height=dp(30),
                                     font_name=font_name_label)
        result_content_layout.add_widget(self.bcv_rate_label)

        # Espaciador explícito entre la tasa BCV y los inputs de USD/Bs (antes era 15dp explícito + 10dp implícito = 25dp)
        result_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(25)))

        # Contenedor para USD y Bs displays
        display_container = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint=(None, None), size=(dp(300), dp(50)),
                                      pos_hint={'center_x': 0.5})

        # TextInput para el valor en USD con formato "$___"
        self.usd_display = TextInput(text='', font_size=dp(18),
                                     foreground_color=(1, 1, 1, 1),
                                     background_color=(0.1, 0.1, 0.1, 1),
                                     padding=[dp(20), dp(12), dp(20), dp(12)],
                                     readonly=True, multiline=False,
                                     size_hint_x=0.4, # Ancho ajustado para USD
                                     halign='center',
                                     cursor_color=(1,1,1,1),
                                     font_name=FONT_BOLD if FONT_BOLD else 'Roboto')
        display_container.add_widget(self.usd_display)

        # TextInput para el valor en Bs con formato "Bs____"
        self.bs_display = TextInput(text='', font_size=dp(18),
                                    foreground_color=(1, 1, 1, 1),
                                    background_color=(0.1, 0.1, 0.1, 1),
                                    padding=[dp(20), dp(12), dp(20), dp(12)],
                                    readonly=True, multiline=False,
                                    size_hint_x=0.6, # Ancho ajustado para Bs
                                    halign='center',
                                    cursor_color=(1,1,1,1),
                                    font_name=FONT_BOLD if FONT_BOLD else 'Roboto')
        display_container.add_widget(self.bs_display)
        result_content_layout.add_widget(display_container)

        # Espaciador entre los outputs y el botón "Volver" (dp(10) para el espacio visible)
        result_content_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        # Botón Volver (usando la clase RoundedShadowButton)
        back_button = RoundedShadowButton(text='Volver', font_size=dp(20),
                             background_color=(0.1, 0.1, 0.1, 1),
                             color=(1, 1, 1, 1),
                             size_hint=(None, None), size=(dp(300), dp(50)),
                             pos_hint={'center_x': 0.5},
                             on_press=self.go_back,
                             font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                             button_radius=[dp(12)] * 4,
                             shadow_radius=[0] * 4,
                             shadow_offset_x=dp(3),
                             shadow_offset_y=dp(3),
                             shadow_color=[1, 1, 1, 1],
                             shadow_spread=dp(2)
                             )

        result_content_layout.add_widget(back_button)

        self.add_widget(result_content_layout) # Añadir el layout de contenido a la pantalla

    def on_enter(self, *args):
        """
        Se llama cuando la pantalla de resultados se hace activa.
        Establece la conversión inicial a BCV y actualiza los displays.
        """
        self.usd_display.text = f"${self.app.usd_amount:.2f}"

        # Por defecto, usar la tasa BCV si está disponible
        if self.app.bcv_rate > 0:
            self.app.set_conversion_rate(self.app.bcv_rate)
        else:
            self.bs_display.text = "Error de tasa"
            self.app.current_conversion_rate = 0

        # Actualizar la visualización de la tasa BCV
        self.update_bcv_display()

    def update_bcv_display(self):
        """
        Actualiza el texto de la tasa BCV y el display de la conversión principal.
        """
        self.bcv_rate_label.text = f"Tasa BCV hoy: {self.app.bcv_rate:.2f} Bs" if self.app.bcv_rate > 0 else "Tasa BCV hoy: No disponible"

        # Actualizar el display de Bolívares con la tasa de conversión actual
        if self.app.current_conversion_rate > 0:
            converted_bs = self.app.usd_amount * self.app.current_conversion_rate
            self.bs_display.text = f"Bs {converted_bs:.2f}"
        else:
            self.bs_display.text = "Error de tasa"


    def go_back(self, instance):
        """Regresa a la pantalla principal."""
        self.manager.current = 'main'


class VesToUsdScreen(Screen):
    """
    Nueva pantalla para la conversión de Bolívar (VES) a USD.
    """
    # ELIMINADO: bcv_rate_text ya no es una propiedad, se elimina la etiqueta

    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = 'ves_to_usd'
        self.app = App.get_running_app()
        self.setup_ui()
        # ELIMINADO: Vinculación a bcv_rate de la app ya no es necesaria para mostrar la tasa en esta pantalla.

    def on_enter(self, *args):
        """
        Se llama cuando la pantalla VES a USD se hace activa.
        Asegura que la tasa BCV se intente cargar o actualizar, aunque no se muestre directamente.
        """
        print(f"DEBUG (VesToUsdScreen.on_enter): Entering VesToUsdScreen. Current app.bcv_rate: {self.app.bcv_rate}")
        # Limpiar cualquier mensaje anterior
        self.message_label.text = ""
        self.usd_result_label.text = "Total en USD: 0.00"
        self.ves_input.text = ""


    def setup_ui(self):
        """Configura la interfaz de usuario de la pantalla de VES a USD."""
        # CAMBIO REALIZADO: Ajustar pos_hint y spacing para que se vea mejor el layout
        ves_usd_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(0), # CAMBIADO: spacing a 0
                                   size_hint=(0.9, None))
        ves_usd_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.2} # Ajustado a 0.2 para subir el contenido


        # Imagen de la moneda
        image_source = 'icono_moneda.png'
        try:
            if not resource_find(image_source):
                print(f"ERROR: La imagen '{image_source}' no se encontró. Se usará un placeholder.")
                image_source = 'https://placehold.co/100x100/gold/white?text=$'
            else:
                print(f"DEBUG: Intentando cargar imagen desde: {resource_find(image_source)}")

            coin_image = Image(source=image_source,
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})

        except Exception as e:
            print(f"ERROR: No se pudo cargar la imagen '{image_source}'. Error: {e}")
            coin_image = Image(source='https://placehold.co/100x100/gold/white?text=$',
                               size_hint=(None, None), size=(dp(100), dp(100)),
                               pos_hint={'center_x': 0.5})
        ves_usd_layout.add_widget(coin_image)

        # ELIMINADO: La etiqueta de la tasa BCV se elimina de esta pantalla

        # Espaciador entre la imagen y el input VES (ajustado para compensar la eliminación de la etiqueta BCV)
        ves_usd_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(40))) # Aumentado el espaciado

        font_name_label = FONT_REGULAR if FONT_REGULAR else 'Roboto' # Se mantiene para otros Labels


        # Input para la cantidad en VES
        self.ves_input = TextInput(hint_text='Valor VES a convertir', font_size=dp(18),
                                   foreground_color=(1, 1, 1, 1),
                                   hint_text_color=(0.7, 0.7, 0.7, 1),
                                   background_color=(0.1, 0.1, 0.1, 1),
                                   padding=[dp(20), dp(12), dp(20), dp(12)],
                                   size_hint_y=None, height=dp(50),
                                   multiline=False, input_type='number',
                                   cursor_color=(1,1,1,1),
                                   font_name=FONT_BOLD if FONT_BOLD else 'Roboto')
        ves_usd_layout.add_widget(self.ves_input)

        # Espaciador entre input y botón
        ves_usd_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        # Botón Convertir VES a USD
        convert_ves_button = RoundedShadowButton(text='Convertir a USD', font_size=dp(20),
                                background_color=(0.1, 0.1, 0.1, 1),
                                color=(1, 1, 1, 1),
                                size_hint_y=None, height=dp(50),
                                on_press=self.convert_ves_to_usd,
                                font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                                button_radius=[dp(12)] * 4,
                                shadow_radius=[0] * 4,
                                shadow_offset_x=dp(3),
                                shadow_offset_y=dp(3),
                                shadow_color=[1, 1, 1, 1],
                                shadow_spread=dp(2)
                                )
        ves_usd_layout.add_widget(convert_ves_button)

        # Nuevo espaciador antes de "Total en USD"
        ves_usd_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        self.usd_result_label = Label(text="Total en USD: 0.00", font_size=dp(18), color=(1,1,1,1),
                                              halign='center', size_hint_y=None, height=dp(30),
                                              font_name=font_name_label)
        ves_usd_layout.add_widget(self.usd_result_label)

        # CAMBIO REALIZADO: Espaciador entre el resultado y el mensaje de error
        ves_usd_layout.add_widget(BoxLayout(size_hint_y=None, height=dp(10)))

        # Etiqueta para mostrar mensajes de error/información
        self.message_label = Label(
            text="",
            font_size='16sp',
            color=(1, 0.2, 0.2, 1), # Rojo para errores
            size_hint_y=None, height=dp(30)
        )
        ves_usd_layout.add_widget(self.message_label)

        # Botón Volver
        back_button = RoundedShadowButton(text='Volver', font_size=dp(20),
                             background_color=(0.1, 0.1, 0.1, 1),
                             color=(1, 1, 1, 1),
                             size_hint_y=None, height=dp(50),
                             on_press=self.go_back,
                             font_name=FONT_BOLD if FONT_BOLD else 'Roboto',
                             button_radius=[dp(12)] * 4,
                             shadow_radius=[0] * 4,
                             shadow_offset_x=dp(3),
                             shadow_offset_y=dp(3),
                             shadow_color=[1, 1, 1, 1],
                             shadow_spread=dp(2)
                             )
        ves_usd_layout.add_widget(back_button)

        self.add_widget(ves_usd_layout)

    def convert_ves_to_usd(self, instance):
        """Convierte VES a USD."""
        self.message_label.text = ""
        try:
            ves_amount = float(self.ves_input.text)
            if ves_amount < 0:
                self.message_label.text = "Por favor, ingrese un valor positivo para VES."
                return
            if self.app.bcv_rate <= 0:
                self.message_label.text = "Tasa BCV no disponible. Intente de nuevo más tarde."
                return
            usd_total = ves_amount / self.app.bcv_rate
            self.usd_result_label.text = f"Total en USD: {usd_total:,.2f}"
            self.ves_input.text = ""
        except ValueError:
            self.message_label.text = "Entrada VES inválida. Ingrese un número."
        except Exception as e:
            self.message_label.text = f"Ocurrió un error: {e}"

    def go_back(self, instance):
        """Regresa a la pantalla principal."""
        self.manager.current = 'main'


class ConverterApp(App):
    """
    Clase principal de la aplicación Kivy.
    Gestiona las pantallas y la tasa de cambio global.
    """
    bcv_rate = NumericProperty(0)
    usd_amount = NumericProperty(0) # Necesario para la ResultScreen original
    current_conversion_rate = NumericProperty(0) # Necesario para la ResultScreen original
    motivational_quote_text = StringProperty("Cargando frase motivacional...")

    def build(self):
        """
        Construye la interfaz de usuario de la aplicación y configura el icono.
        """
        # Establece el título de la aplicación
        self.title = "Convertidor de Moneda"

        # Configuración del icono de la aplicación
        self.icon = resource_find('icono_moneda.png')

        self.sm = ScreenManager()
        # Añadir LoadingScreen primero
        self.loading_screen = LoadingScreen(name='loading')
        self.sm.add_widget(self.loading_screen)

        self.main_screen = MainScreen(name='main')
        self.result_screen = ResultScreen(name='result')
        self.ves_to_usd_screen = VesToUsdScreen(name='ves_to_usd') # Nueva pantalla

        self.sm.add_widget(self.main_screen)
        self.sm.add_widget(self.result_screen)
        self.sm.add_widget(self.ves_to_usd_screen) # Añadir la nueva pantalla

        # Establecer la pantalla de carga como la inicial
        self.sm.current = 'loading'

        # Vincular la propiedad bcv_rate a la etiqueta de BCV en la pantalla de resultados
        self.bind(bcv_rate=lambda instance, value: setattr(self.result_screen, 'bcv_rate_text', f"Tasa BCV hoy: {value:.2f} Bs" if value > 0 else "Tasa BCV hoy: No disponible"))
        # ELIMINADO: Nueva vinculación para la pantalla VES a USD ya no es necesaria aquí.


        # Vincular la tasa de conversión actual para que el display en ResultScreen se actualice.
        self.bind(current_conversion_rate=self.update_result_screen_conversion_display)

        # Nueva vinculación: Cuando la propiedad motivational_quote_text de la App cambie,
        # actualiza la propiedad motivational_quote_text de la MainScreen.
        self.bind(motivational_quote_text=self.main_screen.setter('motivational_quote_text'))

        # Programar la inicialización de datos y el cambio de pantalla después de que la UI se haya construido
        Clock.schedule_once(self.start_app_init_tasks, 0)

        return self.sm

    def start_app_init_tasks(self, dt):
        """
        Inicia las tareas de fetching de datos en segundo plano
        y luego cambia a la pantalla principal.
        """
        # Iniciar las operaciones de fetching que ya están en hilos separados
        self.fetch_rates(0) # El '0' es un placeholder, no afecta el comportamiento de threading
        self.fetch_motivational_quote(0) # Idem

        # Cambiar a la pantalla principal inmediatamente.
        # Los datos se actualizarán asincrónicamente cuando estén listos.
        self.sm.current = 'main'


    def set_conversion_rate(self, rate):
        """
        Establece la tasa de conversión actual.
        """
        self.current_conversion_rate = rate

    def update_result_screen_conversion_display(self, instance, value):
        """
        Callback para actualizar la conversión en la pantalla de resultados
        cuando current_conversion_rate cambia.
        """
        if self.sm.current == 'result':
            self.result_screen.update_bcv_display()

    def fetch_rates(self, dt):
        """
        Inicia la operación de fetching de tasas en un hilo separado
        para evitar que la UI se congele.
        """
        threading.Thread(target=self._fetch_rates_thread).start()

    def _fetch_rates_thread(self):
        """
        Función para obtener la tasa de cambio del BCV de la API en un hilo separado.
        Actualiza la propiedad bcv_rate de la aplicación que luego actualiza la UI.
        """
        base_url = 'https://pydolarve.org/api/v2/dollar'

        # Solo necesitamos el monitor 'bcv'
        monitor_name = 'bcv'
        rate_property = 'bcv_rate'

        try:
            print(f"DEBUG: Attempting to fetch rate for {monitor_name} from: {base_url}?monitor={monitor_name}")
            response = requests.get(f"{base_url}?monitor={monitor_name}")
            response.raise_for_status()
            data = response.json()

            print(f"DEBUG: Raw API response for BCV: {data}")

            if 'price' in data and data['price'] is not None:
                raw_price_str = str(data['price']) # Convertir a cadena para manipularla
                print(f"DEBUG: BCV raw price string: '{raw_price_str}'")

                # Intentar limpiar la cadena de precio
                # Primero, reemplazar comas por puntos (si la API usa comas como decimales)
                cleaned_price_str = raw_price_str.replace(',', '.')

                # Si el formato es como "1.07.62", eliminar el primer punto
                # Esto es una suposición basada en el debug, si el formato cambia, esto podría fallar.
                if cleaned_price_str.count('.') > 1:
                    parts = cleaned_price_str.split('.')
                    if len(parts) > 1 and parts[-1].isdigit(): # Asegurarse de que el último es el decimal
                        cleaned_price_str = "".join(parts[:-1]) + "." + parts[-1]
                    else:
                        # Si no es el formato esperado, intentar eliminar solo el primer punto
                        cleaned_price_str = cleaned_price_str.replace('.', '', 1)


                price = float(cleaned_price_str) if cleaned_price_str.replace('.', '', 1).isdigit() else 0.0
                print(f"DEBUG: Cleaned price string: '{cleaned_price_str}', Converted price: {price}")


                if price > 0:
                    Clock.schedule_once(lambda dt, prop=rate_property, p=price: setattr(self, prop, p), 0)
                    print(f"DEBUG: BCV rate successfully set to {price}")
                else:
                    print(f"Warning: Invalid or zero BCV rate after cleaning: {price}. Showing Not Available.")
                    Clock.schedule_once(lambda dt, prop=rate_property: setattr(self, prop, 0), 0)
            else:
                print(f"The response from {monitor_name} does not contain a valid 'price' or is None: {data}")
                Clock.schedule_once(lambda dt, prop=rate_property: setattr(self, prop, 0), 0)

        except requests.exceptions.RequestException as e:
            print(f"Error: Network or API error when fetching rate for {monitor_name}: {e}")
            Clock.schedule_once(lambda dt, prop=rate_property: setattr(self, prop, 0), 0)
        except json.JSONDecodeError as e:
            print(f"Error: JSON decoding error for {monitor_name}: {e}. Unexpected API response.")
            Clock.schedule_once(lambda dt: setattr(self, prop, 0), 0)
        except Exception as e:
            print(f"Error: An unexpected error occurred for {monitor_name}: {e}")
            Clock.schedule_once(lambda dt: setattr(self, prop, 0), 0)


    def fetch_motivational_quote(self, dt):
        """
        Función para obtener una frase motivacional de la API externa en un hilo separado.
        Actualiza la propiedad motivational_quote_text de la aplicación.
        """
        threading.Thread(target=self._fetch_motivational_quote_thread).start()

    def _fetch_motivational_quote_thread(self):
        """
        Realiza la llamada a la API de frases motivacionales.
        Utiliza una API de frases del día en español.
        """
        api_url = "https://frasedeldia.azurewebsites.net/api/phrase"
        fallback_quote = "Si hoy no fue un buen día, eso está bien porque entonces mañana tal vez lo será."

        try:
            print(f"DEBUG: Attempting to get motivational quote from: {api_url}")
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            print(f"DEBUG: Raw API response for quotes: {data}")

            if 'phrase' in data and data['phrase'].strip():
                quote = data['phrase'].strip()
                print(f"DEBUG: Quote obtained: '{quote}'")
                Clock.schedule_once(lambda dt, q=quote: setattr(self, 'motivational_quote_text', q), 0)
            else:
                print(f"Warning: Motivational quotes API returned empty or unexpected phrase: {data}")
                Clock.schedule_once(lambda dt: setattr(self, 'motivational_quote_text', fallback_quote), 0)

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network or API error when fetching motivational quote: {e}")
            Clock.schedule_once(lambda dt: setattr(self, 'motivational_quote_text', fallback_quote), 0)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decoding error for motivational quote: {e}. Unexpected API response.")
            Clock.schedule_once(lambda dt: setattr(self, 'motivational_quote_text', fallback_quote), 0)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred when fetching motivational quote: {e}")
            Clock.schedule_once(lambda dt: setattr(self, 'motivational_quote_text', fallback_quote), 0)

if __name__ == '__main__':
    ConverterApp().run()