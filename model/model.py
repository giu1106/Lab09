from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {}  # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {}  # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        self._escursioni_parco = []
        self._max_giorni = None
        self._max_budget = None

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        if self.escursioni_map is None or self.punti_interesse_map is None:
            return

        relazioni = EscursioneDAO.get_escursioni_punti_interesse()
        if relazioni is not None:
            for rel in relazioni:
                id_esc = rel["id_escursione"]
                id_poi = rel["id_punto_interesse"]
                if id_esc in self.escursioni_map and id_poi in self.punti_interesse_map:
                    escursione = self.escursioni_map[id_esc]
                    punto = self.punti_interesse_map[id_poi]
                    escursione.punti_interesse.add(punto)
                    punto.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        if self.escursioni_map is None:
            return self._pacchetto_ottimo, self._costo, 0


        self._escursioni_parco = [
            esc for esc in self.escursioni_map.values() if esc.id_parco == id_parco
        ]
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        self._ricorsione(
            start_index=0,
            pacchetto_parziale=[],
            durata_corrente=0,
            costo_corrente=0.0,
            valore_corrente=0,
            punti_usati=set()
        )

        if self._valore_ottimo == -1:
            self._valore_ottimo = 0

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        for i in range(start_index, len(self._escursioni_parco)):
            escursione = self._escursioni_parco[i]

            nuova_durata = durata_corrente + escursione.durata_giorni
            nuovo_costo = costo_corrente + escursione.costo


            if self._max_giorni is not None and nuova_durata > self._max_giorni:
                continue
            if self._max_budget is not None and nuovo_costo > self._max_budget:
                continue
            if not punti_usati.isdisjoint(escursione.punti_interesse):
                continue


            valore_escursione = sum(poi.voto_visitatori for poi in escursione.punti_interesse)
            pacchetto_parziale.append(escursione)
            nuovi_punti_usati = punti_usati.union(escursione.punti_interesse)


            self._ricorsione(
                start_index=i + 1,
                pacchetto_parziale=pacchetto_parziale,
                durata_corrente=nuova_durata,
                costo_corrente=nuovo_costo,
                valore_corrente=valore_corrente + valore_escursione,
                punti_usati=nuovi_punti_usati
            )

            pacchetto_parziale.pop()