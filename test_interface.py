
import interface
from time import sleep

scope = interface.Interface()
for i in range(50):
    scope.render_loading(timestep=i)
    sleep(1/3)
scope.render_main(5, 10)
