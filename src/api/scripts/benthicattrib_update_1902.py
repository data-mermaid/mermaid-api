from api.models.mermaid import BenthicAttribute


class BenthicAttributeUpdateGenerator(object):
    def __init__(self):
        self.macroalgae = BenthicAttribute.objects.get(name="Fleshy macroalgae")
        self.coralline_algae = BenthicAttribute.objects.get(name="Coralline algae")
        self.hard = BenthicAttribute.objects.get(name="Hard coral")
        self.ta = BenthicAttribute.objects.get(name="Turf algae")
        self.clam = BenthicAttribute.objects.get(name="Other clam")
        self.otherinvert = BenthicAttribute.objects.get(name="Other invertebrates")
        self.microbial = BenthicAttribute.objects.get(name="Microbial")

    def _assign_parent(self, name, new_parent=None):
        ba = BenthicAttribute.objects.get(name=name)
        ba.parent = new_parent
        ba.save()
        return ba

    def _reassign_grandchildren(self, grandparent, new_grandparent=None):
        new_grandparent = new_grandparent or grandparent
        children = BenthicAttribute.objects.filter(parent=grandparent)
        for child in children:
            print("{} child: {}".format(grandparent.name, child))
            for grandchild in BenthicAttribute.objects.filter(parent=child):
                print(grandchild)
                grandchild.parent = new_grandparent
                grandchild.save()

    def update(self):
        self._assign_parent("Crustose coralline algae")
        self._assign_parent("Soft coral")
        self._assign_parent("Rubble")
        self._assign_parent("Sand")
        self._assign_parent("Epilithic algal matrix", self.ta)
        self._assign_parent("Bleached coral", self.hard)
        cyan = self._assign_parent("Cyanobacteria")

        self.macroalgae.name = "Macroalgae"
        self.macroalgae.save()
        self.microbial.name = "Microbial mats"
        self.microbial.parent = cyan
        self.microbial.save()
        self.clam.name = "Clam"
        self.clam.save()

        _ = BenthicAttribute.objects.create(name="Sea cucumber", parent=self.otherinvert)
        _ = BenthicAttribute.objects.create(name="Sea urchin", parent=self.otherinvert)

        self._reassign_grandchildren(self.macroalgae)
        self._reassign_grandchildren(self.coralline_algae, self.macroalgae)


# Before running script: backup db
def run():
    ba_update = BenthicAttributeUpdateGenerator()
    ba_update.update()


# after script: delete reassigned children in admin, reassigning transects/CRs as necessary
# Algal assemblage, Brown fleshy algae, Green fleshy algae, Red fleshy algae
# Coralline algae, Brown coralline, red coralline, green coralline algae
