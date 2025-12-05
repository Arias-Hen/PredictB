from django.contrib.admin import SimpleListFilter

class CiudadFilter(SimpleListFilter):
    title = "Ciudad"
    parameter_name = "ciudad"

    def lookups(self, request, model_admin):
        ciudades = set(model_admin.model.objects.values_list("ciudad", flat=True))
        return [(c, c) for c in ciudades]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(ciudad=self.value())
        return queryset


class DistritoFilter(SimpleListFilter):
    title = "Distrito"
    parameter_name = "distrito"

    def lookups(self, request, model_admin):
        distritos = set(model_admin.model.objects.values_list("distrito", flat=True))
        return [(d, d) for d in distritos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(distrito=self.value())
        return queryset


class BarrioFilter(SimpleListFilter):
    title = "Barrio"
    parameter_name = "barrio"

    def lookups(self, request, model_admin):
        barrios = set(model_admin.model.objects.values_list("barrio", flat=True))
        return [(b, b) for b in barrios]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(barrio=self.value())
        return queryset
class CalleFilter(SimpleListFilter):
    title = "Calle"
    parameter_name = "calle"

    def lookups(self, request, model_admin):
        barrios = set(model_admin.model.objects.values_list("calle", flat=True))
        return [(b, b) for b in barrios]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(barrio=self.value())
        return queryset
