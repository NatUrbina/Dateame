from driver.driver_pool import DriverPool

# DriverPool(10)


from providers.mercado_libre.MercadoLibre import MercadoLibreProvider

MercadoLibreProvider("https://listado.mercadolibre.com.pe/_CustId_84683920").run()